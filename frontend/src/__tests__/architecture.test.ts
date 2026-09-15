import test from "node:test";
import assert from "node:assert/strict";
import { colors } from "../theme/colors";

test("Theme color palette preserves Obsidian Luxe design system tokens", () => {
  assert.equal(colors.background, "#05080E");
  assert.equal(colors.surface, "#0E1420");
  assert.equal(colors.surfaceCard, "rgba(14, 20, 32, 0.85)");
  assert.equal(colors.gold, "#F59E0B");
  assert.equal(colors.emerald, "#10B981");
  assert.equal(colors.sky, "#38BDF8");
  assert.equal(colors.violet, "#8B5CF6");
});

test("Theme palette defines high-contrast text and border tokens", () => {
  assert.ok(colors.textPrimary);
  assert.ok(colors.textSecondary);
  assert.ok(colors.surfaceBorder);
  assert.ok(colors.surfaceBorderActive);
  assert.ok(colors.emeraldLight);
  assert.ok(colors.goldLight);
});
