package app.odrig.operators;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** A bounded serial capture; the caller runs readFrom on its own I/O worker. */
public final class UsbCapture {
    public interface Port extends AutoCloseable {
        int read(byte[] bytes, int timeoutMs) throws IOException;
        void write(byte[] bytes, int timeoutMs) throws IOException;
        void close() throws IOException;
    }
    public interface Connector {
        Port open() throws IOException;
    }
    public static final int LIMIT = 1024 * 1024;
    public static final int TAIL = 32768;
    private final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    private long generation;
    private long started;
    private String device = "";
    private String state = "idle";
    private String detail = "";
    private boolean active;
    private boolean requested;
    private int requests;

    public synchronized long prepare(String label) {
        if (active) throw new IllegalStateException("Stop the current capture first.");
        generation++;
        started = System.currentTimeMillis();
        bytes.reset();
        device = label;
        state = "permission";
        detail = "Waiting for USB permission.";
        active = true;
        requested = false;
        requests = 0;
        return generation;
    }

    public synchronized boolean current(long token) {
        return active && generation == token;
    }

    public synchronized void fail(long token, String message) {
        if (!current(token)) return;
        active = false;
        state = "error";
        detail = message == null ? "USB connection failed." : message.substring(0, Math.min(512, message.length()));
    }

    public synchronized void stop(String reason) {
        generation++;
        if (active) {
            state = "stopped";
            detail = reason;
        }
        active = false;
        requested = false;
    }

    public synchronized boolean requestDiagnostics() {
        if (!active || !state.equals("capturing")) return false;
        requested = true;
        return true;
    }

    private synchronized boolean takeRequest(long token) {
        if (!current(token) || !requested) return false;
        requested = false;
        requests++;
        return true;
    }

    private synchronized boolean append(long token, byte[] data, int count) throws IOException {
        if (!current(token)) return false;
        if (count < 0 || count > data.length) throw new IOException("Invalid USB read length.");
        bytes.write(data, 0, Math.min(count, LIMIT - bytes.size()));
        if (bytes.size() == LIMIT) {
            active = false;
            state = "limit";
            detail = "Capture stopped at 1 MiB. Share this log before starting another.";
        }
        return active;
    }

    public void readFrom(long token, Connector connector) {
        if (!current(token)) return;
        try (Port port = connector.open()) {
            synchronized (this) {
                if (!current(token)) return;
                state = "capturing";
                detail = "Listening at 115200. Waiting for board output.";
            }
            byte[] chunk = new byte[4096];
            while (current(token)) {
                if (takeRequest(token)) port.write("status\nfault\n".getBytes(StandardCharsets.US_ASCII), 1000);
                int count = port.read(chunk, 200);
                if (!append(token, chunk, count)) break;
            }
        } catch (IOException | RuntimeException error) {
            fail(token, "USB: " + error.getMessage() + " Close the flasher or other USB apps and retry.");
        }
    }

    public synchronized String state() { return state; }
    public synchronized String detail() { return detail; }
    public synchronized boolean active() { return active; }
    public synchronized int size() { return bytes.size(); }
    public synchronized String tail() {
        byte[] all = bytes.toByteArray();
        return new String(all, Math.max(0, all.length - TAIL), Math.min(TAIL, all.length), StandardCharsets.UTF_8);
    }
    public synchronized String exportText() {
        return "Odrig USB diagnostics\nPhone start time (Unix ms): " + started +
            "\nDevice: " + device + "\nSerial: 115200 8N1\nState: " + state +
            "\nDetail: " + detail + "\nReceived bytes: " + bytes.size() +
            "\nStatus/fault requests: " + requests +
            "\nText decoding: UTF-8 (invalid bytes replaced)\n--- board output ---\n" +
            new String(bytes.toByteArray(), StandardCharsets.UTF_8);
    }
}
