import app.odrig.operators.UsbCapture;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public final class UsbCaptureCheck {
    private static void check(boolean value, String why) {
        if (!value) throw new AssertionError(why);
    }
    private static class Port implements UsbCapture.Port {
        int reads;
        int writes;
        int closes;
        public int read(byte[] bytes, int timeout) throws IOException { reads++; throw new IOException("unplugged"); }
        public void write(byte[] bytes, int timeout) {
            check(new String(bytes, StandardCharsets.US_ASCII).equals("status\nfault\n"), "Only the diagnostic reads are allowed");
            writes++;
        }
        public void close() { closes++; }
    }
    public static void main(String[] args) {
        UsbCapture capture = new UsbCapture();
        long token = capture.prepare("test port");
        switch (args[0]) {
            case "cancel": {
                capture.stop("stopped");
                capture.readFrom(token, () -> { throw new AssertionError("Late permission opened USB"); });
                check(capture.state().equals("stopped"), "Stop state retained");
                break;
            }
            case "staleOpen": {
                Port port = new Port();
                capture.readFrom(token, () -> { capture.stop("cancelled during open"); capture.prepare("new port"); return port; });
                check(port.closes == 1 && port.reads == 0, "Obsolete open must close without reading");
                check(capture.state().equals("permission") && capture.size() == 0, "New session stays intact");
                break;
            }
            case "overlap": {
                try { capture.prepare("other"); throw new AssertionError("Overlapping capture accepted"); }
                catch (IllegalStateException expected) { check(capture.current(token), "First capture survives rejected overlap"); }
                break;
            }
            case "denied": {
                capture.fail(token, "permission denied");
                check(!capture.active() && capture.detail().equals("permission denied"), "Denied permission visible");
                long next = capture.prepare("retry");
                capture.fail(token, "late failure");
                check(capture.current(next), "Late failure must not damage retry");
                break;
            }
            case "passive": {
                Port port = new Port();
                capture.readFrom(token, () -> port);
                check(port.writes == 0 && port.closes == 1, "Capture is passive and closes on unplug");
                check(!capture.active() && capture.detail().contains("unplugged"), "Read failure visible");
                break;
            }
            case "readReports": {
                Port port = new Port() {
                    public int read(byte[] bytes, int timeout) throws IOException {
                        check(capture.requestDiagnostics(), "Read diagnostics enabled during capture");
                        if (reads++ == 0) return 0;
                        throw new IOException("unplugged");
                    }
                };
                check(!capture.requestDiagnostics(), "No writes while permission pending");
                capture.readFrom(token, () -> port);
                check(port.writes == 1, "Only an explicit request writes reports");
                break;
            }
            case "utf8": {
                byte[] data = "rst:0x1\nשלום\n<script>bad()</script>\n".getBytes(StandardCharsets.UTF_8);
                Port port = new Port() {
                    int at;
                    public int read(byte[] bytes, int timeout) throws IOException {
                        if (at == data.length) throw new IOException("unplugged");
                        bytes[0] = data[at++];
                        return 1;
                    }
                };
                capture.readFrom(token, () -> port);
                check(capture.tail().equals(new String(data, StandardCharsets.UTF_8)), "Fragmented UTF-8 preserved");
                capture.stop("stopped");
                check(capture.size() == data.length && capture.exportText().contains("שלום"), "Log survives stop/export");
                check(capture.exportText().contains("Received bytes: " + data.length), "Export has capture metadata");
                break;
            }
            case "limit": {
                Port port = new Port() {
                    public int read(byte[] bytes, int timeout) { Arrays.fill(bytes, (byte) 'X'); return bytes.length; }
                };
                capture.readFrom(token, () -> port);
                check(capture.size() == UsbCapture.LIMIT && capture.tail().length() == UsbCapture.TAIL, "Bounded full log and displayed tail");
                check(capture.state().equals("limit") && port.closes == 1, "Limit visibly stops and closes port");
                check(capture.exportText().endsWith("X".repeat(UsbCapture.LIMIT)), "Export keeps the whole bounded capture");
                break;
            }
            case "stopRead": {
                Port port = new Port() {
                    public int read(byte[] bytes, int timeout) {
                        check(timeout > 0 && timeout <= 250, "Read timeout must allow prompt stop");
                        capture.stop("background");
                        capture.prepare("replacement");
                        bytes[0] = 'X'; return 1;
                    }
                };
                capture.readFrom(token, () -> port);
                check(capture.size() == 0 && capture.state().equals("permission") && port.closes == 1, "Late read cannot populate replacement capture");
                break;
            }
            default: throw new AssertionError("Unknown scenario");
        }
        System.out.println("PASS " + args[0]);
    }
}
