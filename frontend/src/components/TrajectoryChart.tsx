import React, { useState } from "react";
import {
  Dimensions,
  GestureResponderEvent,
  LayoutChangeEvent,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import Svg, {
  Circle,
  Defs,
  Line,
  LinearGradient,
  Path,
  Rect,
  Stop,
  Text as SvgText,
} from "react-native-svg";
import { TrajectoryPoint } from "../types";
import { colors } from "../theme/colors";

interface TrajectoryChartProps {
  points: TrajectoryPoint[];
  minimumReserve: number;
  height?: number;
}

export const TrajectoryChart: React.FC<TrajectoryChartProps> = ({
  points,
  minimumReserve,
  height = 220,
}) => {
  const [chartWidth, setChartWidth] = useState<number>(
    Dimensions.get("window").width - 40
  );
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (!points || points.length === 0) {
    return (
      <View style={[styles.container, { height }]}>
        <Text style={styles.emptyText}>No trajectory points available</Text>
      </View>
    );
  }

  const onLayout = (event: LayoutChangeEvent) => {
    const { width } = event.nativeEvent.layout;
    if (width > 0) setChartWidth(width);
  };

  const paddingLeft = 45;
  const paddingRight = 16;
  const paddingTop = 25;
  const paddingBottom = 30;

  const innerWidth = Math.max(10, chartWidth - paddingLeft - paddingRight);
  const innerHeight = Math.max(10, height - paddingTop - paddingBottom);

  // Compute min and max values across points and reserve
  const allBalances = points.map((p) => p.baseline_balance);
  const withPurchaseBalances = points
    .map((p) => p.with_purchase_balance)
    .filter((b): b is number => b !== null && b !== undefined);

  const combined = [...allBalances, ...withPurchaseBalances, minimumReserve];
  const rawMin = Math.min(...combined);
  const rawMax = Math.max(...combined);

  // Pad domain for visual breathing room
  const yMin = Math.max(0, Math.floor(rawMin * 0.85));
  const yMax = Math.ceil(rawMax * 1.15);
  const yRange = yMax - yMin || 1;

  const scaleX = (index: number) => {
    return paddingLeft + (index / (points.length - 1)) * innerWidth;
  };

  const scaleY = (val: number) => {
    const normalized = (val - yMin) / yRange;
    return paddingTop + innerHeight - normalized * innerHeight;
  };

  // Build SVG Path strings
  let baselinePath = "";
  let baselineAreaPath = "";
  let purchasePath = "";

  points.forEach((p, idx) => {
    const x = scaleX(idx);
    const y = scaleY(p.baseline_balance);
    if (idx === 0) {
      baselinePath = `M ${x} ${y}`;
      baselineAreaPath = `M ${x} ${scaleY(yMin)} L ${x} ${y}`;
    } else {
      baselinePath += ` L ${x} ${y}`;
      baselineAreaPath += ` L ${x} ${y}`;
    }
  });

  const lastX = scaleX(points.length - 1);
  const baseY = scaleY(yMin);
  baselineAreaPath += ` L ${lastX} ${baseY} Z`;

  const hasPurchase = points.some((p) => p.with_purchase_balance !== null && p.with_purchase_balance !== undefined);
  if (hasPurchase) {
    points.forEach((p, idx) => {
      const val = p.with_purchase_balance ?? p.baseline_balance;
      const x = scaleX(idx);
      const y = scaleY(val);
      purchasePath += idx === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });
  }

  // Find lowest point on baseline
  let lowestIdx = 0;
  points.forEach((p, idx) => {
    if (p.baseline_balance < points[lowestIdx].baseline_balance) {
      lowestIdx = idx;
    }
  });

  const reserveY = scaleY(minimumReserve);

  const handleTouch = (evt: GestureResponderEvent) => {
    const touchX = evt.nativeEvent.locationX;
    const clampedX = Math.max(paddingLeft, Math.min(chartWidth - paddingRight, touchX));
    const ratio = (clampedX - paddingLeft) / innerWidth;
    const targetIdx = Math.round(ratio * (points.length - 1));
    setSelectedIndex(Math.max(0, Math.min(points.length - 1, targetIdx)));
  };

  const selectedPoint = selectedIndex !== null ? points[selectedIndex] : null;

  return (
    <View style={styles.container} onLayout={onLayout}>
      {/* Interactive Tooltip Inspector */}
      {selectedPoint ? (
        <View style={styles.tooltipContainer}>
          <Text style={styles.tooltipDate}>{selectedPoint.date}</Text>
          <View style={styles.tooltipRow}>
            <Text style={styles.tooltipLabel}>Baseline: </Text>
            <Text style={styles.tooltipValue}>${selectedPoint.baseline_balance.toFixed(2)}</Text>
            {selectedPoint.with_purchase_balance !== null && selectedPoint.with_purchase_balance !== undefined ? (
              <>
                <Text style={[styles.tooltipLabel, { marginLeft: 8 }]}>With Purchase: </Text>
                <Text style={[styles.tooltipValue, { color: colors.warning }]}>
                  ${selectedPoint.with_purchase_balance.toFixed(2)}
                </Text>
              </>
            ) : null}
          </View>
        </View>
      ) : null}

      <TouchableOpacity
        activeOpacity={1}
        onPress={handleTouch}
        style={{ width: chartWidth, height }}
      >
        <Svg width={chartWidth} height={height}>
          <Defs>
            <LinearGradient id="baselineAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0%" stopColor={colors.primary} stopOpacity="0.35" />
              <Stop offset="100%" stopColor={colors.primary} stopOpacity="0.0" />
            </LinearGradient>
          </Defs>

          {/* Grid lines and Y labels */}
          {[0, 0.33, 0.66, 1].map((pct, i) => {
            const val = yMin + yRange * pct;
            const y = scaleY(val);
            return (
              <React.Fragment key={i}>
                <Line
                  x1={paddingLeft}
                  y1={y}
                  x2={chartWidth - paddingRight}
                  y2={y}
                  stroke={colors.surfaceBorder}
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <SvgText
                  x={paddingLeft - 8}
                  y={y + 4}
                  fill={colors.textMuted}
                  fontSize="10"
                  textAnchor="end"
                >
                  ${Math.round(val)}
                </SvgText>
              </React.Fragment>
            );
          })}

          {/* Reserve Line (Safety Invariant) */}
          <Line
            x1={paddingLeft}
            y1={reserveY}
            x2={chartWidth - paddingRight}
            y2={reserveY}
            stroke={colors.danger}
            strokeWidth="1.5"
            strokeDasharray="6 4"
          />
          <SvgText
            x={chartWidth - paddingRight}
            y={reserveY - 6}
            fill={colors.danger}
            fontSize="9"
            fontWeight="bold"
            textAnchor="end"
          >
            Reserve Buffer (${minimumReserve})
          </SvgText>

          {/* Area under curve */}
          <Path d={baselineAreaPath} fill="url(#baselineAreaGrad)" />

          {/* Baseline Curve */}
          <Path
            d={baselinePath}
            fill="none"
            stroke={colors.primary}
            strokeWidth="2.5"
          />

          {/* Prospective Purchase Curve */}
          {hasPurchase ? (
            <Path
              d={purchasePath}
              fill="none"
              stroke={colors.warning}
              strokeWidth="2"
              strokeDasharray="5 3"
            />
          ) : null}

          {/* Lowest Point Marker */}
          <Circle
            cx={scaleX(lowestIdx)}
            cy={scaleY(points[lowestIdx].baseline_balance)}
            r="4.5"
            fill={colors.danger}
            stroke={colors.white}
            strokeWidth="1.5"
          />

          {/* Selected Point Marker */}
          {selectedIndex !== null ? (
            <>
              <Line
                x1={scaleX(selectedIndex)}
                y1={paddingTop}
                x2={scaleX(selectedIndex)}
                y2={paddingTop + innerHeight}
                stroke={colors.white}
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <Circle
                cx={scaleX(selectedIndex)}
                cy={scaleY(points[selectedIndex].baseline_balance)}
                r="6"
                fill={colors.primary}
                stroke={colors.white}
                strokeWidth="2"
              />
            </>
          ) : null}

          {/* X Axis Date labels */}
          <SvgText
            x={paddingLeft}
            y={height - 8}
            fill={colors.textMuted}
            fontSize="10"
            textAnchor="start"
          >
            Day 0 ({points[0]?.date.slice(5)})
          </SvgText>
          <SvgText
            x={scaleX(Math.floor(points.length / 2))}
            y={height - 8}
            fill={colors.textMuted}
            fontSize="10"
            textAnchor="middle"
          >
            Day 45
          </SvgText>
          <SvgText
            x={chartWidth - paddingRight}
            y={height - 8}
            fill={colors.textMuted}
            fontSize="10"
            textAnchor="end"
          >
            Day 90 ({points[points.length - 1]?.date.slice(5)})
          </SvgText>
        </Svg>
      </TouchableOpacity>

      {/* Legend */}
      <View style={styles.legendRow}>
        <View style={styles.legendItem}>
          <View style={[styles.legendIndicator, { backgroundColor: colors.primary }]} />
          <Text style={styles.legendText}>Baseline 90d</Text>
        </View>
        {hasPurchase ? (
          <View style={styles.legendItem}>
            <View style={[styles.legendIndicator, { backgroundColor: colors.warning }]} />
            <Text style={styles.legendText}>With Purchase</Text>
          </View>
        ) : null}
        <View style={styles.legendItem}>
          <View style={[styles.legendIndicator, { backgroundColor: colors.danger }]} />
          <Text style={styles.legendText}>Minimum Reserve</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
    overflow: "hidden",
  },
  emptyText: {
    color: colors.textMuted,
    textAlign: "center",
    marginTop: 40,
    fontSize: 13,
  },
  tooltipContainer: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginHorizontal: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  tooltipDate: {
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: "600",
  },
  tooltipRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 2,
  },
  tooltipLabel: {
    fontSize: 11,
    color: colors.textMuted,
  },
  tooltipValue: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  legendRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 10,
    gap: 16,
  },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
  },
  legendIndicator: {
    width: 10,
    height: 3,
    borderRadius: 2,
    marginRight: 6,
  },
  legendText: {
    fontSize: 11,
    color: colors.textSecondary,
    fontWeight: "500",
  },
});
