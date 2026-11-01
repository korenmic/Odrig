import re
import unittest

from . import support

MAIN = support.APP / "android" / "app" / "src" / "main"
JAVA = MAIN / "java" / "app" / "odrig" / "operators"


class TheSender(unittest.TestCase):
    """Source checks for the Wi-Fi sender and the native app shell."""

    @classmethod
    def setUpClass(cls):
        cls.sender = (JAVA / "TargetPlugin.java").read_text(encoding="utf-8")
        cls.activity = (JAVA / "MainActivity.java").read_text(encoding="utf-8")
        cls.manifest = (MAIN / "AndroidManifest.xml").read_text(encoding="utf-8")

    def test_native_classes_are_the_shell_wifi_sender_and_usb_capture(self):
        self.assertEqual(sorted(path.name for path in JAVA.iterdir()),
                         ["MainActivity.java", "TargetPlugin.java", "UsbCapture.java", "UsbDiagnosticsPlugin.java"])

    def test_the_web_code_calls_the_sender_by_the_names_it_has(self):
        self.assertIn('@CapacitorPlugin(name = "Target")', self.sender)
        methods = re.findall(r"@PluginMethod\s+public void ([a-z]+)\(", self.sender)
        self.assertEqual(methods, ["send", "route", "usb", "connect", "write", "read"])
        target = (support.WWW / "target.js").read_text(encoding="utf-8")
        called = re.findall(r'nativePromise\("([A-Za-z]+)", "([a-z]+)"', target)
        self.assertEqual(called, [("Target", "send"), ("Target", "route")])
        for method in ("connect", "read", "write"):
            self.assertIn(f'call("{method}"', target)
        for member in ("address", "line", "timeoutMs"):
            self.assertIn(f'call.getString("{member}")' if member != "timeoutMs" else 'call.getInt("timeoutMs"', self.sender)
            self.assertRegex(target, rf"\b{member}\b")
        for member in ("status", "body", "wifi", "validated", "portal", "others"):
            self.assertIn(f'.put("{member}"', self.sender)
            self.assertRegex(target, rf"\.{member}\b")
        # The two codes of a refusal are the two kinds of failure the web code knows.
        self.assertEqual(sorted(set(re.findall(r'reject\([^;]*"([a-z-]+)"\);', self.sender))), ["no-answer", "no-usb", "no-wifi", "usb-refused"])
        self.assertIn('error.code === "no-wifi"', target)
        self.assertIn('code === "no-usb" || code === "usb-refused"', target)

    def test_a_line_is_sent_on_the_wifi_network_once_as_it_is(self):
        for expected in (
            ".addTransportType(NetworkCapabilities.TRANSPORT_WIFI)",
            ".removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)",
            "networks.requestNetwork(request, watch);",
            'over.openConnection(new URL("http://" + address + "/odrig"), Proxy.NO_PROXY)',
            'connection.setRequestMethod("POST");',
            'connection.setRequestProperty("Content-Type", "application/octet-stream");',
            'connection.setRequestProperty("Connection", "close");',
            "connection.setFixedLengthStreamingMode(body.length);",
            "connection.setConnectTimeout(limit);",
            "connection.setReadTimeout(limit);",
            "connection.setInstanceFollowRedirects(false);",
            "networks.unregisterNetworkCallback(watch);",
            "line.getBytes(StandardCharsets.UTF_8)",
        ):
            self.assertEqual(self.sender.count(expected), 1, expected)
        self.assertEqual(self.sender.count("openConnection("), 1)
        self.assertIn("MOST_BODY = 4096", self.sender)

    def test_the_board_is_opened_on_its_usb_serial_port_without_a_reset(self):
        for expected in (
            "VENDOR = 0x303a;",
            "PRODUCT = 0x1001;",
            "found.getVendorId() == VENDOR && found.getProductId() == PRODUCT",
            "UsbConstants.USB_CLASS_CDC_DATA",
            "opened.claimInterface(bulk, true)",
            "LINE_CODING = {(byte) 0x00, (byte) 0xC2, (byte) 0x01, (byte) 0x00, 0, 0, 8};",
            "opened.controlTransfer(0x21, 0x20, 0, index, LINE_CODING, LINE_CODING.length, TRANSFER_MS);",
            # Both modem lines lowered by one request: DTR low while RTS is high is never made.
            "opened.controlTransfer(0x21, 0x22, 0, index, null, 0, TRANSFER_MS);",
            'new Intent(GRANT).setPackage(getContext().getPackageName())',
            "Context.RECEIVER_NOT_EXPORTED",
        ):
            self.assertEqual(self.sender.count(expected), 1, expected)
        self.assertEqual(self.sender.count("controlTransfer("), 2)
        # The detach is heard, and closes the port of the device that went.
        self.assertEqual(self.sender.count("UsbManager.ACTION_USB_DEVICE_DETACHED"), 2)
        self.assertIn('<uses-feature android:name="android.hardware.usb.host" android:required="false" />', self.manifest)
        self.assertIn('<action android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED" />', self.manifest)
        device = (MAIN / "res" / "xml" / "usb_device.xml").read_text(encoding="utf-8")
        self.assertIn('<usb-device vendor-id="12346" product-id="4097" />', device)
        self.assertEqual((0x303A, 0x1001), (12346, 4097))

    def test_it_binds_no_process_reads_no_network_name_and_looks_into_no_line(self):
        for word in ("bindProcessToNetwork", "WifiManager", "getSSID", "WifiInfo", "LOCATION", "getConnectionInfo", "setProcessDefaultNetwork"):
            self.assertNotIn(word, self.sender + self.activity + self.manifest, word)
        # No word of a command and no member of a reply is in the Java code.
        for word in ('"status"', '"body"'):
            self.assertEqual(self.sender.count(word), 1, word)
        self.assertNotRegex(self.sender, r'"(play|brightness|list|on|off|ok|error|playing|animation)\b')

    def test_the_activity_registers_the_sender_first_and_keeps_the_screen_on(self):
        register = self.activity.index("registerPlugin(TargetPlugin.class);")
        create = self.activity.index("super.onCreate(savedInstanceState);")
        keep = self.activity.index("getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);")
        self.assertLess(register, create)
        self.assertLess(create, keep)

    def test_the_manifest_asks_for_three_permissions_and_allows_plain_http(self):
        asked = re.findall(r'<uses-permission android:name="android\.permission\.([A-Z_]+)" />', self.manifest)
        self.assertEqual(asked, ["INTERNET", "ACCESS_NETWORK_STATE", "CHANGE_NETWORK_STATE"])
        self.assertEqual(self.manifest.count("uses-permission"), 3)
        self.assertIn('android:networkSecurityConfig="@xml/network_security_config"', self.manifest)
        config = (MAIN / "res" / "xml" / "network_security_config.xml").read_text(encoding="utf-8")
        self.assertIn('<base-config cleartextTrafficPermitted="true" />', config)
        self.assertNotIn("usesCleartextTraffic", self.manifest)


if __name__ == "__main__":
    unittest.main()
