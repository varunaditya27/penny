import test from "node:test";
import assert from "node:assert/strict";
import { colors } from "../theme/colors";

test("Theme color palette preserves Obsidian Luxe design system tokens", () => {
  assert.equal(colors.background, "#000000");
  assert.equal(colors.surface, "#101010");
  assert.equal(colors.surfaceCard, "rgba(18, 18, 18, 0.96)");
  assert.equal(colors.gold, "#F59E0B");
  assert.equal(colors.primary, "#F59E0B");
  assert.equal(colors.emerald, "#10B981");
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
