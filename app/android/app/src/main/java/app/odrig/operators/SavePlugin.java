package app.odrig.operators;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.util.Base64;

import androidx.activity.result.ActivityResult;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Saves a file the web code made, a download or a backup, where the operator chooses. The
 * bytes come in pieces of base64 and are written to one file of the app's cache; then the
 * system's dialog of the Storage Access Framework asks for the place and the name, and the
 * file is copied there. The cache's file is removed once it is saved or the dialog is
 * closed, when the web code abandons it, and when the next file begins.
 */
@CapacitorPlugin(name = "Save")
public class SavePlugin extends Plugin {
    private static final String FOLDER = "saving";
    private static final int BUFFER = 65536;

    private final ExecutorService copier = Executors.newSingleThreadExecutor();
    private File file;
    private OutputStream output;
    private String name;
    private String type;

    @Override
    public void load() {
        drop();
    }

    @Override
    protected void handleOnDestroy() {
        drop();
        copier.shutdownNow();
    }

    /** Closes the file being written, if any, and removes the cache's files. */
    private synchronized void drop() {
        if (output != null) {
            try {
                output.close();
            } catch (IOException ignored) {
                // The file is removed in any case.
            }
            output = null;
        }
        File folder = new File(getContext().getCacheDir(), FOLDER);
        File[] left = folder.listFiles();
        if (left != null) {
            for (File one : left) {
                one.delete();
            }
        }
        file = null;
    }

    /** Begins a file with the name `name` and the media type `type`. */
    @PluginMethod
    public void begin(PluginCall call) {
        String asked = call.getString("name");
        String kind = call.getString("type", "application/octet-stream");
        if (asked == null || asked.isEmpty() || asked.contains("/") || kind == null) {
            call.reject("The file has no name it can be saved under.");
            return;
        }
        drop();
        synchronized (this) {
            try {
                File folder = new File(getContext().getCacheDir(), FOLDER);
                if (!folder.isDirectory() && !folder.mkdirs()) {
                    throw new IOException("no folder in the cache");
                }
                file = new File(folder, "file");
                output = new FileOutputStream(file);
                name = asked;
                type = kind;
                call.resolve();
            } catch (IOException error) {
                call.reject("The phone could not write the file: " + error.getMessage());
            }
        }
        if (output == null) {
            drop();
        }
    }

    /** Adds the bytes of `data`, in base64, to the file begun. */
    @PluginMethod
    public void append(PluginCall call) {
        String data = call.getString("data");
        synchronized (this) {
            if (output == null || data == null) {
                call.reject("No file is begun.");
                return;
            }
            try {
                output.write(Base64.decode(data, Base64.DEFAULT));
                call.resolve();
                return;
            } catch (IOException | IllegalArgumentException error) {
                call.reject("The phone could not write the file: " + error.getMessage());
            }
        }
        drop();
    }

    /** Drops the file begun, which is not to be saved. */
    @PluginMethod
    public void abandon(PluginCall call) {
        drop();
        call.resolve();
    }

    /**
     * Ends the file and asks the operator where to keep it. Resolves with `saved` true and
     * the `name` asked for once it is copied there, or `saved` false when the dialog was
     * closed without a place.
     */
    @PluginMethod
    public void finish(PluginCall call) {
        synchronized (this) {
            if (output == null) {
                call.reject("No file is begun.");
                return;
            }
            try {
                output.close();
            } catch (IOException error) {
                output = null;
                call.reject("The phone could not write the file: " + error.getMessage());
                return;
            }
            output = null;
        }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType(type)
            .putExtra(Intent.EXTRA_TITLE, name);
        startActivityForResult(call, intent, "chosen");
    }

    @ActivityCallback
    private void chosen(PluginCall call, ActivityResult result) {
        if (call == null) {
            drop();
            return;
        }
        Intent data = result.getData();
        Uri place = data == null ? null : data.getData();
        if (result.getResultCode() != Activity.RESULT_OK || place == null) {
            drop();
            JSObject answer = new JSObject();
            answer.put("saved", false);
            call.resolve(answer);
            getBridge().releaseCall(call);
            return;
        }
        final File written = file;
        final String asked = name;
        copier.execute(() -> {
            try (InputStream input = new FileInputStream(written);
                 OutputStream copy = getContext().getContentResolver().openOutputStream(place)) {
                if (copy == null) {
                    throw new IOException("the place chosen cannot be written");
                }
                byte[] buffer = new byte[BUFFER];
                for (int count = input.read(buffer); count > 0; count = input.read(buffer)) {
                    copy.write(buffer, 0, count);
                }
                JSObject answer = new JSObject();
                answer.put("saved", true);
                answer.put("name", asked);
                call.resolve(answer);
            } catch (IOException | SecurityException error) {
                call.reject("The phone could not save the file: " + error.getMessage());
            } finally {
                drop();
                getBridge().executeOnMainThread(() -> getBridge().releaseCall(call));
            }
        });
    }
}
