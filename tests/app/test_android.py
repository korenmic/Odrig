import re
import unittest

from . import support

MAIN = support.APP / "android" / "app" / "src" / "main"
JAVA = MAIN / "java" / "app" / "odrig" / "operators"


class TheSender(unittest.TestCase):
    """What the app's Android code says. No test runs it: it needs a phone."""

    @classmethod
    def setUpClass(cls):
        cls.sender = (JAVA / "TargetPlugin.java").read_text(encoding="utf-8")
        cls.activity = (JAVA / "MainActivity.java").read_text(encoding="utf-8")
        cls.manifest = (MAIN / "AndroidManifest.xml").read_text(encoding="utf-8")

    def test_the_app_has_two_classes_of_its_own(self):
        self.assertEqual(sorted(path.name for path in JAVA.iterdir()), ["MainActivity.java", "TargetPlugin.java"])

    def test_the_web_code_calls_the_sender_by_the_names_it_has(self):
        self.assertIn('@CapacitorPlugin(name = "Target")', self.sender)
        methods = re.findall(r"@PluginMethod\s+public void ([a-z]+)\(", self.sender)
        self.assertEqual(methods, ["send", "route"])
        target = (support.WWW / "target.js").read_text(encoding="utf-8")
        called = re.findall(r'nativePromise\("([A-Za-z]+)", "([a-z]+)"', target)
        self.assertEqual(called, [("Target", "send"), ("Target", "route")])
        for member in ("address", "line", "timeoutMs"):
            self.assertIn(f'call.getString("{member}")' if member != "timeoutMs" else 'call.getInt("timeoutMs"', self.sender)
            self.assertRegex(target, rf"\b{member}\b")
        for member in ("status", "body", "wifi", "validated", "portal", "others"):
            self.assertIn(f'.put("{member}"', self.sender)
            self.assertRegex(target, rf"\.{member}\b")
        # The two codes of a refusal are the two kinds of failure the web code knows.
        self.assertEqual(sorted(set(re.findall(r'call\.reject\([^;]*"([a-z-]+)"\);', self.sender))), ["no-answer", "no-wifi"])
        self.assertIn('error.code === "no-wifi"', target)

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
