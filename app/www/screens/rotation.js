import * as client from '../client.js';
import {Refusal} from '../commands.js';

const byId = id => document.getElementById(id);
let visible = false;
let version = -1;
let epoch = 0;
let connected = false;
let saved = null;
let unsupported = false;
let phase = null;
let problem = '';

function ready() {
  return visible && !document.hidden && client.state.link === 'answers' && client.state.statusFresh;
}

function reset() {
  ++epoch;
  saved = null;
  unsupported = false;
  phase = null;
  problem = '';
}

function draw() {
  const field = byId('output-rotation');
  field.value = saved === null ? '' : String(saved.degrees);
  field.disabled = !ready() || phase !== null || unsupported || saved?.supported !== true;
  byId('rotation-refresh').disabled = !ready() || phase !== null;
  let text = !ready() ? 'Connect to the board to confirm its output rotation.' :
    phase === 'saving' ? 'Saving rotation... Waiting for the board to confirm.' :
    phase === 'reading' ? 'Reading output rotation...' :
    unsupported ? 'This target does not support square output rotation. Other controls remain available.' :
    saved?.error ? 'The saved rotation could not be read. Output uses 0 degrees; choose an angle to repair it.' :
    saved ? `Confirmed output: ${saved.degrees} degrees clockwise.` : 'Refresh to read the output rotation.';
  if (problem && ready() && phase === null) text = `${problem} ${text}`;
  byId('rotation-state').textContent = text;
}

function permission(at, target) {
  return () => epoch === at && version === target && client.targetVersion() === target && ready();
}

function saveProblem(error) {
  if (!(error instanceof Refusal)) return 'No confirmed save reply.';
  if (error.code === 'busy') return 'The installation is busy. Try again after it finishes.';
  if (error.code === 'rotation-conflict') return 'Another controller changed the rotation. Its saved angle is read again.';
  if (error.code === 'in-use') return 'Stop the mapping test before changing output rotation.';
  if (error.code === 'storage-error') return 'The board could not save the rotation. Its saved angle is read again.';
  return 'The board refused to save the rotation. Its saved angle is read again.';
}

async function read(keepProblem = false) {
  if (!ready() || phase !== null) return;
  const at = epoch;
  const allowed = permission(at, version);
  if (!keepProblem) problem = '';
  phase = 'reading';
  draw();
  try {
    const reply = await client.rotationRead(allowed);
    if (at !== epoch || reply === false) return;
    saved = reply;
    unsupported = !reply.supported;
  } catch (error) {
    if (at !== epoch) return;
    unsupported = error instanceof Refusal && ['unknown-command', 'unsupported'].includes(error.code);
    if (!unsupported) problem = 'Could not confirm the rotation. Refresh to try again.';
  } finally {
    if (at === epoch) { phase = null; draw(); }
  }
}

async function change() {
  if (!ready() || phase !== null || unsupported || saved?.supported !== true) { draw(); return; }
  const degrees = Number(byId('output-rotation').value);
  if (![0, 90, 180, 270].includes(degrees)) { draw(); return; }
  const at = epoch;
  const allowed = permission(at, version);
  const revision = saved.revision;
  let reconcile = false;
  phase = 'saving';
  problem = '';
  draw();
  try {
    const reply = await client.rotationSet(revision, degrees, allowed);
    if (at !== epoch || reply === false) return;
    saved = reply;
  } catch (error) {
    if (at !== epoch) return;
    problem = saveProblem(error);
    reconcile = true;
  } finally {
    if (at === epoch) {
      phase = null;
      draw();
      if (reconcile) await read(true);
    }
  }
}

function synchronize() {
  const nextVersion = client.targetVersion();
  const nextConnected = client.state.link === 'answers' && client.state.statusFresh;
  if (nextVersion !== version || connected && !nextConnected) reset();
  version = nextVersion;
  connected = nextConnected;
  draw();
  if (ready() && phase === null && saved === null && !unsupported && !problem) void read();
}

export function showing(value) {
  if (visible === value) return;
  visible = value;
  reset();
  synchronize();
}

export function start() {
  byId('output-rotation').addEventListener('change', () => void change());
  byId('rotation-refresh').addEventListener('click', () => void read());
  document.addEventListener('visibilitychange', () => { reset(); synchronize(); });
  client.watch(synchronize);
}
