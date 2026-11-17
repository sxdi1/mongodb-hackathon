import test from "node:test";
import assert from "node:assert/strict";
import { allocate, calculateReceipt, demoReducer, members, sampleItems, snapshot } from "../src/lib/demo.ts";

test("sample receipt conserves all cents in equal and itemized splits", () => {
  const equal = calculateReceipt(sampleItems, "equal");
  assert.deepEqual(equal, { subtotal: 10400, tax: 1352, tip: 1560, total: 13312, shares: [3328, 3328, 3328, 3328] });
  const itemized = calculateReceipt(sampleItems, "itemized");
  assert.deepEqual(itemized.shares, [3712, 3200, 3456, 2944]);
  assert.equal(itemized.shares.reduce((a, b) => a + b, 0), itemized.total);
});
test("rounding, zero receipts, and shared line items never lose cents", () => {
  for (let cents = 0; cents < 1000; cents++) {
    const items = [{ id: "test", name: "Dinner", cents, owner: "all" }];
    for (const mode of ["equal", "itemized"]) {
      const result = calculateReceipt(items, mode);
      assert.equal(result.shares.reduce((a, b) => a + b, 0), result.total);
      assert.ok(result.shares.every(n => Number.isInteger(n) && n >= 0));
    }
  }
  assert.deepEqual(allocate(3, [1, 1, 1, 1]), [1, 1, 1, 0]);
  assert.deepEqual(allocate(0, [0, 0, 0, 0]), [0, 0, 0, 0]);
});
test("a booking requires all four votes, which can be changed before booking", () => {
  let state = snapshot(2);
  assert.equal(demoReducer(state, { type: "book" }).step, 2);
  for (const member of members) state = demoReducer(state, { type: "vote", id: member.id });
  state = demoReducer(state, { type: "vote", id: "maya" });
  assert.equal(state.votes.length, 3);
  state = demoReducer(state, { type: "vote", id: "maya" });
  assert.equal(demoReducer(state, { type: "book" }).step, 3);
  assert.deepEqual(demoReducer(state, { type: "activity", id: "golf" }).votes, []);
});
test("receipt acknowledgment needs sent then received; repeats are harmless", () => {
  let state = snapshot(8);
  state = demoReducer(state, { type: "payment", id: "sarah", kind: "received" });
  assert.equal(state.payments.sarah, "unpaid");
  for (const id of ["sarah", "omar", "maya"]) {
    state = demoReducer(state, { type: "payment", id, kind: "sent" });
    assert.equal(state.payments[id], "sent");
    state = demoReducer(state, { type: "payment", id, kind: "sent" });
    assert.equal(state.payments[id], "sent");
    state = demoReducer(state, { type: "payment", id, kind: "received" });
    assert.equal(state.payments[id], "settled");
  }
  assert.equal(state.step, 10);
});
test("changing amounts or split method invalidates all debtor acknowledgments", () => {
  const settled = snapshot(10);
  assert.equal(demoReducer(settled, { type: "mode", mode: "equal" }), settled);
  for (const action of [{ type: "item", id: "bowl", cents: 2201 }, { type: "mode", mode: "itemized" }]) {
    const state = demoReducer(settled, action);
    assert.equal(state.step, 8);
    assert.equal(state.payments.sarah, "unpaid");
    assert.equal(state.payments.omar, "unpaid");
    assert.equal(state.payments.maya, "unpaid");
  }
});
test("full guided demo, backtracking, replay, and reset are deterministic", () => {
  let state = snapshot(0);
  for (let step = 1; step <= 10; step++) {
    state = demoReducer(state, { type: "goto", step });
    assert.equal(state.step, step);
  }
  assert.ok(Object.values(state.payments).every(s => s === "settled"));
  state = demoReducer(state, { type: "goto", step: 5 });
  assert.deepEqual(state, snapshot(5));
  state = demoReducer(state, { type: "goto", step: 9 });
  assert.equal(state.payments.sarah, "sent");
  assert.deepEqual(demoReducer(state, { type: "reset" }), snapshot(0));
  assert.equal(demoReducer(state, { type: "goto", step: -1 }).step, 0);
  assert.equal(demoReducer(state, { type: "goto", step: 90 }).step, 10);
});
