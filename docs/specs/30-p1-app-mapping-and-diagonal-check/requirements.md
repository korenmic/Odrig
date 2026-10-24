# Requirements: app mapping and a diagonal check

## 1. Whole-snake assignments

1.1 The shared app shall show the twenty logical snakes in canvas order with their three column numbers and assigned GPIOs.
1.2 Editing shall only permute the twenty existing pins; choosing another occupied pin swaps assignments. Geometry, direction and output count shall not change.
1.3 Draft edits shall require Save; Cancel reloads the saved assignment. Restore defaults creates a draft only when the current pin set equals GPIO 1-18, 21 and 47.
1.4 The core shall reject incomplete, duplicate, foreign-pin and stale updates without changing the target. Unsupported bench mappings shall remain playable and shall not be editable.

## 2. Durable live routing

2.1 A save shall atomically replace the existing mapping.json and update per-pin routing without rebooting or re-uploading media.
2.2 Storage failure or power loss shall leave the old or new complete mapping. No refresh shall combine two routing assignments.
2.3 Saves shall preserve all show files, animation settings and playback progression. They shall work while the diagnostic is displayed.
2.4 Every command route shall implement the same read, complete-assignment save and diagnostic controls; odrigctl shall expose them.
2.5 Clients shall read authoritative state, detect concurrent edits and recover from lost replies without claiming an unconfirmed save.

## 3. Diagonal diagnostic

3.1 Show diagonal shall pause the show and repeatedly display exactly sixty white pixels at x=y on black, using the same decoder and mapping as ordinary playback.
3.2 Its tracked JSON source shall be encoded only with the JavaScript converter and packaged into each build. It shall require no show entry, upload, user storage or seed 29 implementation.
3.3 Stop diagonal shall restart the previously current animation in its playlist or cycle. If it disappeared, use the first available playlist animation or idle. Explicit play shall exit the test.
3.4 Repeated start/stop requests shall be idempotent. Restart shall keep the mapping but leave diagnostic mode off. A disconnected app shall not stop a target-wide test.
3.5 Power, brightness and current limiting shall remain under their existing controls. Off stays dark. Upload and remove are busy during a test; read commands and mapping changes remain available.
3.6 The app shall distinguish draft versus saved mapping and describe the expected bottom-left to top-right line. Physical confirmation belongs to a person.

## 4. Hosts, packaging and acceptance

4.1 The APK, browser app and emulator Controller shall share one implementation. The emulator shall update its Mapping view and served mapping without restarting.
4.2 WLED output routing shall use the complete committed assignment, synchronized with refresh copying. The fallback output adapter shall support equivalent pin-based routing without expanding seed 12 into a full player here.
4.3 Tests shall inspect actual per-pin bytes, not just a logical canvas. Old mappings and protocol limits remain valid.
4.4 Build and verify the APK and both firmware variants through repository tools. No flash, hardware change or phone installation is authorized in this run.
4.5 Owner acceptance on the real twenty-snake installation remains a separate unchecked task until the owner runs it. Never claim that test passed from emulator evidence.
