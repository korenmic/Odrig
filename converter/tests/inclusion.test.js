import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {ROOT} from "./support.js";
import path from "node:path";
import {show, pack} from "../lib/index.js";
const source = (item) => new TextEncoder().encode(JSON.stringify({version:1,brightness:32,items:[item]}));
test("show preserves strict optional playlist inclusion and pack keeps its bytes", () => {
  for (const ignored of [true,false]) {
    const bytes = source({id:1,file:"hello.odrg",ignored});
    assert.equal(show.loads(bytes).items[0].ignored, ignored);
    const files = pack.pack({mapping:new Uint8Array(fs.readFileSync(path.join(ROOT,"mapping/legs-2.json"))),show:bytes,sources:{"hello.json":new Uint8Array(fs.readFileSync(path.join(ROOT,"animations/hello.json")))}});
    assert.deepEqual(files.get("show.json"), bytes);
  }
});
test("inclusion refuses nonboolean values and cycles", () => {
  for (const ignored of [0,1,"true",null,[],{}]) assert.throws(() => show.loads(source({id:1,file:"a.odrg",ignored})), /show-malformed/);
  assert.throws(() => show.loads(source({id:1,cycle:[1],seconds:1,ignored:false})), /show-malformed/);
});
