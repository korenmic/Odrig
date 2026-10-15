package app.odrig.operators;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * The sender: carries one command line to the target on the phone's Wi-Fi network,
 * whatever network the phone uses for its other traffic. The network of an installation
 * has no internet, and a request that is not opened on it would leave through mobile
 * data. The sender looks into no line and no reply.
 */
@CapacitorPlugin(name = "Target")
public class TargetPlugin extends Plugin {
    /** A reply is one line of at most 1,024 bytes; more than this of a body is not read. */
    private static final int MOST_BODY = 4096;
    private static final int LIMIT_MS = 5000;

    private ConnectivityManager networks;
    private volatile Network wifi;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

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
    }

    @Override
    protected void handleOnDestroy() {
        networks.unregisterNetworkCallback(watch);
        worker.shutdownNow();
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
