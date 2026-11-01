package app.odrig.operators;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.net.Uri;

import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@CapacitorPlugin(name = "UsbDiagnostics")
public class UsbDiagnosticsPlugin extends Plugin {
    private final UsbCapture capture = new UsbCapture();
    private final ExecutorService reader = Executors.newSingleThreadExecutor();
    private final ExecutorService files = Executors.newSingleThreadExecutor();
    private UsbManager manager;
    private String permissionAction;
    private UsbSerialPort pending;
    private long pendingToken;
    private String connectedDevice;
    private volatile boolean foreground = true;

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            synchronized (UsbDiagnosticsPlugin.this) {
                if (permissionAction.equals(intent.getAction())) {
                    long token = intent.getLongExtra("capture", -1);
                    if (pending == null || token != pendingToken || !capture.current(token)) return;
                    UsbSerialPort port = pending;
                    pending = null;
                    if (manager.hasPermission(port.getDriver().getDevice())) connect(port, token);
                    else capture.fail(token, "USB permission was denied. Tap Start capture to try again.");
                } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(intent.getAction())) {
                    UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    if (device != null && device.getDeviceName().equals(connectedDevice)) stopCapture("USB device disconnected. Captured text is kept.");
                }
            }
        }
    };

    @Override public void load() {
        manager = (UsbManager) getContext().getSystemService(Context.USB_SERVICE);
        permissionAction = getContext().getPackageName() + ".USB_DIAGNOSTIC_PERMISSION";
        IntentFilter filter = new IntentFilter(permissionAction);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        ContextCompat.registerReceiver(getContext(), receiver, filter, ContextCompat.RECEIVER_NOT_EXPORTED);
    }

    @Override protected void handleOnResume() { foreground = true; }

    @Override protected void handleOnStop() {
        foreground = false;
        stopCapture("App left the foreground. Captured text is kept.");
    }

    @Override protected void handleOnDestroy() {
        foreground = false;
        stopCapture("App closed.");
        getContext().unregisterReceiver(receiver);
        reader.shutdown();
        files.shutdown();
    }

    private synchronized void stopCapture(String reason) {
        pending = null;
        connectedDevice = null;
        capture.stop(reason);
    }

    private JSObject snapshot() {
        synchronized (capture) {
            JSObject result = new JSObject();
            result.put("state", capture.state());
            result.put("detail", capture.detail());
            result.put("active", capture.active());
            result.put("bytes", capture.size());
            result.put("text", capture.tail());
            return result;
        }
    }

    @PluginMethod public void status(PluginCall call) { call.resolve(snapshot()); }

    @PluginMethod public void devices(PluginCall call) {
        JSArray ports = new JSArray();
        boolean host = getContext().getPackageManager().hasSystemFeature("android.hardware.usb.host");
        if (host && manager != null) {
            for (UsbSerialDriver driver : UsbSerialProber.getDefaultProber().findAllDrivers(manager)) {
                UsbDevice device = driver.getDevice();
                for (UsbSerialPort port : driver.getPorts()) {
                    JSObject item = new JSObject();
                    item.put("device", device.getDeviceName());
                    item.put("port", port.getPortNumber());
                    item.put("label", String.format(java.util.Locale.ROOT, "%s %04x:%04x — port %d",
                        driver.getClass().getSimpleName().replace("SerialDriver", ""), device.getVendorId(), device.getProductId(), port.getPortNumber() + 1));
                    ports.put(item);
                }
            }
        }
        JSObject result = new JSObject();
        result.put("supported", host);
        result.put("ports", ports);
        result.put("attached", manager == null ? 0 : manager.getDeviceList().size());
        call.resolve(result);
    }

    @PluginMethod public synchronized void open(PluginCall call) {
        if (!foreground) { call.reject("Return to the foreground before starting USB capture."); return; }
        String name = call.getString("device", "");
        int index = call.getInt("port", -1);
        long prepared = -1;
        try {
            for (UsbSerialDriver driver : UsbSerialProber.getDefaultProber().findAllDrivers(manager)) {
                if (!driver.getDevice().getDeviceName().equals(name)) continue;
                for (UsbSerialPort port : driver.getPorts()) {
                    if (port.getPortNumber() != index) continue;
                    long token = capture.prepare(driver.getClass().getSimpleName() + " " + name + " port " + (index + 1));
                    prepared = token;
                    connectedDevice = name;
                    if (manager.hasPermission(driver.getDevice())) connect(port, token);
                    else {
                        pending = port;
                        pendingToken = token;
                        Intent intent = new Intent(permissionAction).setPackage(getContext().getPackageName());
                        intent.putExtra("capture", token);
                        PendingIntent permission = PendingIntent.getBroadcast(getContext(), (int) token, intent,
                            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                        manager.requestPermission(driver.getDevice(), permission);
                    }
                    call.resolve(snapshot());
                    return;
                }
            }
            call.reject("The selected USB port is no longer connected.");
        } catch (RuntimeException error) {
            if (prepared >= 0) capture.fail(prepared, "Cannot start USB capture: " + error.getMessage());
            if (!capture.active()) connectedDevice = null;
            call.reject(error.getMessage());
        }
    }

    private void connect(UsbSerialPort port, long token) {
        reader.execute(() -> capture.readFrom(token, () -> {
            UsbDeviceConnection connection = manager.openDevice(port.getDriver().getDevice());
            if (connection == null) throw new IOException("Cannot open USB device. Permission may have changed or another app is using it.");
            try {
                port.open(connection);
                port.setRTS(false);
                port.setDTR(false);
                port.setParameters(115200, UsbSerialPort.DATABITS_8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
            } catch (IOException | RuntimeException error) {
                try { port.close(); } catch (Exception ignored) { }
                connection.close();
                throw error;
            }
            return new UsbCapture.Port() {
                @Override public int read(byte[] bytes, int timeoutMs) throws IOException { return port.read(bytes, timeoutMs); }
                @Override public void write(byte[] bytes, int timeoutMs) throws IOException { port.write(bytes, timeoutMs); }
                @Override public void close() throws IOException {
                    try { port.close(); } finally { connection.close(); }
                }
            };
        }));
    }

    @PluginMethod public void stop(PluginCall call) {
        stopCapture("Capture stopped. Captured text is kept.");
        call.resolve(snapshot());
    }

    @PluginMethod public void diagnostics(PluginCall call) {
        if (!capture.requestDiagnostics()) call.reject("Start a USB capture first.");
        else call.resolve();
    }

    @PluginMethod public void share(PluginCall call) {
        if (capture.size() == 0) { call.reject("No board output has been captured yet."); return; }
        stopCapture("Capture stopped for sharing. Captured text is kept.");
        String text = capture.exportText();
        files.execute(() -> {
            try {
                File directory = new File(getContext().getCacheDir(), "diagnostics");
                if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create log folder.");
                File file = new File(directory, "odrig-usb-log.txt");
                try (FileOutputStream output = new FileOutputStream(file)) { output.write(text.getBytes(StandardCharsets.UTF_8)); }
                Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", file);
                Intent send = new Intent(Intent.ACTION_SEND).setType("text/plain");
                send.putExtra(Intent.EXTRA_STREAM, uri);
                send.setClipData(ClipData.newRawUri("Odrig USB diagnostics", uri));
                send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                getActivity().runOnUiThread(() -> {
                    try { getActivity().startActivity(Intent.createChooser(send, "Share USB log")); call.resolve(); }
                    catch (RuntimeException error) { call.reject("Cannot open log sharing: " + error.getMessage()); }
                });
            } catch (IOException | RuntimeException error) { call.reject("Cannot share USB log: " + error.getMessage()); }
        });
    }
}
