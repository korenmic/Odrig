package app.odrig.operators;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginHandle;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * The sender: carries one command line to the target on the phone's Wi-Fi network,
 * whatever network the phone uses for its other traffic. The network of an installation
 * has no internet, and a request that is not opened on it would leave through mobile
 * data. It also carries bytes to and from the board's USB serial port, the ESP32-S3's
 * own, with Android's USB host API. The sender looks into no line and no reply.
 */
@CapacitorPlugin(name = "Target")
public class TargetPlugin extends Plugin {
    /** A reply is one line of at most 1,024 bytes; more than this of a body is not read. */
    private static final int MOST_BODY = 4096;
    private static final int LIMIT_MS = 5000;
    /** The vendor and the product of the ESP32-S3's USB serial port. */
    private static final int VENDOR = 0x303a;
    private static final int PRODUCT = 0x1001;
    /** The broadcast of Android's answer to the question for the device. */
    private static final String GRANT = "app.odrig.operators.USB_GRANT";
    /** The most bytes one read gives back. */
    private static final int MOST_READ = 4096;
    private static final int TRANSFER_MS = 1000;
    /** The longest wait for the other user of the board's port to close it. */
    static final int HANDOVER_MS = 2000;
    /** SET_LINE_CODING of CDC: 115,200 baud, little-endian, one stop bit, no parity, 8 data bits. */
    private static final byte[] LINE_CODING = {(byte) 0x00, (byte) 0xC2, (byte) 0x01, (byte) 0x00, 0, 0, 8};

    private ConnectivityManager networks;
    private volatile Network wifi;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    /** The USB side runs on a thread of its own, apart from the requests over Wi-Fi. */
    private final ExecutorService serial = Executors.newSingleThreadExecutor();
    private UsbManager usb;
    private UsbDevice device;
    private UsbDeviceConnection link;
    private UsbInterface data;
    private UsbEndpoint fromBoard;
    private UsbEndpoint toBoard;
    /** A connect that waits for the operator's answer to Android's question. */
    private PluginCall asking;

    private final BroadcastReceiver usbEvents = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            final String action = intent.getAction();
            final boolean granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false);
            final UsbDevice gone = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
            serial.execute(() -> {
                if (GRANT.equals(action)) {
                    PluginCall call = asking;
                    asking = null;
                    if (call == null) {
                        return;
                    }
                    if (granted) {
                        open(call);
                    } else {
                        call.reject("the USB device was not allowed", "usb-refused");
                    }
                } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(action) && gone != null && device != null && gone.getDeviceId() == device.getDeviceId()) {
                    closeSerial();
                }
            });
        }
    };

    private final ConnectivityManager.NetworkCallback watch = new ConnectivityManager.NetworkCallback() {
        @Override
        public void onAvailable(Network network) {
            wifi = network;
        }

        @Override
        public void onLost(Network network) {
            if (network.equals(wifi)) {
                wifi = null;
            }
        }
    };

    /**
     * Asks the system for a network with the Wi-Fi transport that need not have internet.
     * The network of an installation satisfies that, and the request tells the system
     * that an app needs it.
     */
    @Override
    public void load() {
        networks = (ConnectivityManager) getContext().getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkRequest request = new NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build();
        networks.requestNetwork(request, watch);
        usb = (UsbManager) getContext().getSystemService(Context.USB_SERVICE);
        IntentFilter heard = new IntentFilter(GRANT);
        heard.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= 33) {
            getContext().registerReceiver(usbEvents, heard, Context.RECEIVER_NOT_EXPORTED);
        } else {
            getContext().registerReceiver(usbEvents, heard);
        }
    }

    @Override
    protected void handleOnDestroy() {
        networks.unregisterNetworkCallback(watch);
        getContext().unregisterReceiver(usbEvents);
        serial.execute(this::closeSerial);
        worker.shutdownNow();
        serial.shutdown();
    }

    /**
     * Sends `line` to `http://<address>/odrig` on the Wi-Fi network, once, and resolves
     * with the status and the body of the answer. Without a Wi-Fi network it is refused
     * with the code `no-wifi`, and when no answer comes within `timeoutMs`, with
     * `no-answer`.
     */
    @PluginMethod
    public void send(final PluginCall call) {
        final String address = call.getString("address");
        final String line = call.getString("line");
        final int limit = call.getInt("timeoutMs", LIMIT_MS);
        final Network over = wifi;
        if (address == null || line == null) {
            call.reject("an address and a line are needed", "no-answer");
            return;
        }
        if (over == null) {
            call.reject("the phone is on no Wi-Fi network", "no-wifi");
            return;
        }
        worker.execute(() -> {
            HttpURLConnection connection = null;
            try {
                byte[] body = line.getBytes(StandardCharsets.UTF_8);
                connection = (HttpURLConnection) over.openConnection(new URL("http://" + address + "/odrig"), Proxy.NO_PROXY);
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(limit);
                connection.setReadTimeout(limit);
                connection.setUseCaches(false);
                connection.setInstanceFollowRedirects(false);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/octet-stream");
                connection.setRequestProperty("Connection", "close");
                // A body of fixed length is not sent a second time by the HTTP layer.
                connection.setFixedLengthStreamingMode(body.length);
                try (OutputStream out = connection.getOutputStream()) {
                    out.write(body);
                }
                int status = connection.getResponseCode();
                InputStream answer = status == HttpURLConnection.HTTP_OK ? connection.getInputStream() : connection.getErrorStream();
                JSObject reply = new JSObject();
                reply.put("status", status);
                reply.put("body", answer == null ? "" : text(answer));
                call.resolve(reply);
            } catch (IOException | RuntimeException failure) {
                call.reject(String.valueOf(failure.getMessage()), "no-answer");
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    /**
     * Says how requests travel: whether there is a Wi-Fi network, whether the system has
     * found internet on it or a page to sign in, and what the phone's other traffic uses.
     * The name of the network is not read, which would need the location permission.
     */
    @PluginMethod
    public void route(PluginCall call) {
        Network over = wifi;
        NetworkCapabilities of = over == null ? null : networks.getNetworkCapabilities(over);
        Network usual = networks.getActiveNetwork();
        NetworkCapabilities others = usual == null ? null : networks.getNetworkCapabilities(usual);
        String transport = "none";
        if (others != null) {
            transport = others.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ? "wifi"
                : others.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ? "mobile" : "other";
        }
        JSObject found = new JSObject();
        found.put("wifi", over != null);
        found.put("validated", of != null && of.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED));
        found.put("portal", of != null && of.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL));
        found.put("others", transport);
        call.resolve(found);
    }

    /** Whether a device is the ESP32-S3's USB serial port, the port of this link. */
    static boolean isBoard(UsbDevice found) {
        return found.getVendorId() == VENDOR && found.getProductId() == PRODUCT;
    }

    /** The board on USB: the device of the ESP32-S3's USB serial port, or null. */
    private UsbDevice board() {
        if (usb == null) {
            return null;
        }
        for (UsbDevice found : usb.getDeviceList().values()) {
            if (isBoard(found)) {
                return found;
            }
        }
        return null;
    }

    /**
     * Closes the board's port when it is the device of this name, so that a USB capture can
     * open it; the next `connect` opens it again. Waits at most `HANDOVER_MS` for the USB
     * thread. Not on the USB thread.
     */
    void release(String name) {
        try {
            serial.submit(() -> {
                if (device != null && device.getDeviceName().equals(name)) {
                    closeSerial();
                }
            }).get(HANDOVER_MS, TimeUnit.MILLISECONDS);
        } catch (InterruptedException stopped) {
            Thread.currentThread().interrupt();
        } catch (ExecutionException | TimeoutException | RuntimeException late) {
            // The capture opens the port anyway; the link's next line then reports the lost port.
        }
    }

    /** The plugin of the USB capture, which may hold the board's port, or null. */
    private UsbDiagnosticsPlugin capture() {
        PluginHandle handle = getBridge() == null ? null : getBridge().getPlugin("UsbDiagnostics");
        Plugin found = handle == null ? null : handle.getInstance();
        return found instanceof UsbDiagnosticsPlugin ? (UsbDiagnosticsPlugin) found : null;
    }

    /** Says whether the phone has USB host, whether the board is there, allowed and open. */
    @PluginMethod
    public void usb(final PluginCall call) {
        serial.execute(() -> {
            UsbDevice found = board();
            JSObject state = new JSObject();
            state.put("host", getContext().getPackageManager().hasSystemFeature(PackageManager.FEATURE_USB_HOST));
            state.put("device", found != null);
            state.put("permitted", found != null && usb.hasPermission(found));
            state.put("open", link != null);
            call.resolve(state);
        });
    }

    /**
     * Opens the board's USB serial port, asking Android for the device first when the app
     * may not use it yet. Refused with `no-usb` without the board, with `usb-refused` when
     * the operator did not allow it, and with `no-answer` when it cannot be opened.
     */
    @PluginMethod
    public void connect(final PluginCall call) {
        serial.execute(() -> {
            if (link != null) {
                call.resolve();
                return;
            }
            UsbDevice found = board();
            if (found == null) {
                call.reject("no board is connected by USB", "no-usb");
                return;
            }
            if (usb.hasPermission(found)) {
                open(call);
                return;
            }
            if (asking != null) {
                asking.reject("asked again", "usb-refused");
            }
            asking = call;
            Intent grant = new Intent(GRANT).setPackage(getContext().getPackageName());
            int flags = Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0;
            usb.requestPermission(found, PendingIntent.getBroadcast(getContext(), 0, grant, flags));
        });
    }

    /**
     * Opens the device: its CDC data interface with its two bulk endpoints, the line at
     * 115,200 8N1, and both modem lines lowered by one request, so that DTR low while RTS
     * is high, the pair that resets the chip, is never made. On the USB thread.
     */
    private void open(PluginCall call) {
        UsbDevice found = board();
        if (found == null) {
            call.reject("no board is connected by USB", "no-usb");
            return;
        }
        UsbInterface control = null;
        UsbInterface bulk = null;
        for (int at = 0; at < found.getInterfaceCount(); at++) {
            UsbInterface one = found.getInterface(at);
            if (one.getInterfaceClass() == UsbConstants.USB_CLASS_COMM && control == null) {
                control = one;
            } else if (one.getInterfaceClass() == UsbConstants.USB_CLASS_CDC_DATA && bulk == null) {
                bulk = one;
            }
        }
        UsbEndpoint in = null;
        UsbEndpoint out = null;
        for (int at = 0; bulk != null && at < bulk.getEndpointCount(); at++) {
            UsbEndpoint end = bulk.getEndpoint(at);
            if (end.getType() == UsbConstants.USB_ENDPOINT_XFER_BULK) {
                if (end.getDirection() == UsbConstants.USB_DIR_IN) {
                    in = end;
                } else {
                    out = end;
                }
            }
        }
        if (in == null || out == null) {
            call.reject("the board's USB port has no serial interface", "no-answer");
            return;
        }
        // A capture of this port stops and says that this link took it; its text is kept.
        UsbDiagnosticsPlugin capture = capture();
        if (capture != null) {
            capture.yieldPort(found.getDeviceName());
        }
        UsbDeviceConnection opened = usb.openDevice(found);
        if (opened == null || !opened.claimInterface(bulk, true)) {
            if (opened != null) {
                opened.close();
            }
            call.reject("the board's USB port cannot be opened", "no-answer");
            return;
        }
        int index = control == null ? 0 : control.getId();
        opened.controlTransfer(0x21, 0x20, 0, index, LINE_CODING, LINE_CODING.length, TRANSFER_MS);
        opened.controlTransfer(0x21, 0x22, 0, index, null, 0, TRANSFER_MS);
        device = found;
        link = opened;
        data = bulk;
        fromBoard = in;
        toBoard = out;
        call.resolve();
    }

    /** Closes the board's USB serial port. On the USB thread. */
    private void closeSerial() {
        if (link != null) {
            link.releaseInterface(data);
            link.close();
        }
        link = null;
        data = null;
        fromBoard = null;
        toBoard = null;
        device = null;
    }

    /** Writes `text` to the board's USB serial port, as it is. */
    @PluginMethod
    public void write(final PluginCall call) {
        final String text = call.getString("text");
        serial.execute(() -> {
            if (link == null) {
                call.reject("no board is connected by USB", "no-usb");
                return;
            }
            byte[] bytes = (text == null ? "" : text).getBytes(StandardCharsets.ISO_8859_1);
            int done = 0;
            byte[] piece = new byte[MOST_READ];
            while (done < bytes.length) {
                int length = Math.min(piece.length, bytes.length - done);
                System.arraycopy(bytes, done, piece, 0, length);
                int sent = link.bulkTransfer(toBoard, piece, length, TRANSFER_MS);
                if (sent <= 0) {
                    closeSerial();
                    call.reject("the board's USB port took nothing", "no-usb");
                    return;
                }
                done += sent;
            }
            call.resolve();
        });
    }

    /**
     * Gives back what the board's USB serial port sent, waiting at most `timeoutMs` for the
     * first bytes: `{text}`, empty when nothing came.
     */
    @PluginMethod
    public void read(final PluginCall call) {
        final int wait = Math.max(1, call.getInt("timeoutMs", 0));
        serial.execute(() -> {
            if (link == null) {
                call.reject("no board is connected by USB", "no-usb");
                return;
            }
            ByteArrayOutputStream kept = new ByteArrayOutputStream();
            byte[] piece = new byte[Math.max(64, fromBoard.getMaxPacketSize())];
            int got = link.bulkTransfer(fromBoard, piece, piece.length, wait);
            while (got > 0) {
                kept.write(piece, 0, got);
                got = kept.size() + piece.length <= MOST_READ ? link.bulkTransfer(fromBoard, piece, piece.length, 1) : 0;
            }
            JSObject answer = new JSObject();
            answer.put("text", new String(kept.toByteArray(), StandardCharsets.ISO_8859_1));
            call.resolve(answer);
        });
    }

    private static String text(InputStream answer) throws IOException {
        ByteArrayOutputStream kept = new ByteArrayOutputStream();
        byte[] piece = new byte[1024];
        try (InputStream in = answer) {
            int read;
            while (kept.size() < MOST_BODY && (read = in.read(piece, 0, Math.min(piece.length, MOST_BODY - kept.size()))) != -1) {
                kept.write(piece, 0, read);
            }
        }
        return new String(kept.toByteArray(), StandardCharsets.UTF_8);
    }
}
