import React from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Stop } from "react-native-svg";
import { colors } from "../theme/colors";
import { ShieldCheckIcon } from "./icons";

interface ReserveGaugeProps {
  availableBalance: number;
  minimumReserve: number;
  size?: number;
  strokeWidth?: number;
}

export const ReserveGauge: React.FC<ReserveGaugeProps> = ({
  availableBalance,
  minimumReserve,
  size = 130,
  strokeWidth = 9,
}) => {
  const headroom = availableBalance - minimumReserve;
  const isSafe = headroom >= 0;
  const ratio = minimumReserve > 0 ? availableBalance / minimumReserve : 1;
  const coveragePercent = Math.round(ratio * 100);

  // Geometry calculations
  const center = size / 2;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Clamped progress (0 to 1, where 1.0 represents 200% reserve or fully robust)
  const normalizedProgress = Math.min(1, Math.max(0.04, ratio / 2));
  const strokeDashoffset = circumference * (1 - normalizedProgress);

  const activeColor = isSafe
    ? ratio >= 1.5
      ? colors.emerald
      : colors.gold
    : colors.danger;

  const activeGlow = isSafe
    ? ratio >= 1.5
      ? colors.emeraldGlow
      : colors.goldGlow
    : colors.dangerLight;

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <Defs>
          <LinearGradient id="gaugeGrad" x1="0" y1="1" x2="1" y2="0">
            <Stop
              offset="0%"
              stopColor={isSafe ? colors.gold : colors.dangerDark}
            />
            <Stop
              offset="100%"
              stopColor={isSafe ? colors.emerald : colors.danger}
            />
          </LinearGradient>
        </Defs>

        {/* Ambient Glow Backing */}
        <Circle
          cx={center}
          cy={center}
          r={radius}
          stroke={activeGlow}
          strokeWidth={strokeWidth + 6}
          strokeOpacity={0.4}
          fill="none"
        />

        {/* Background Track */}
        <Circle
          cx={center}
          cy={center}
          r={radius}
          stroke={colors.surfaceBorderLight}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
        />

        {/* Dynamic Progress Arc */}
        <Circle
          cx={center}
          cy={center}
          r={radius}
          stroke="url(#gaugeGrad)"
          strokeWidth={strokeWidth}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
          fill="none"
        />
      </Svg>

      {/* Center Readout */}
      <View style={styles.centerContent}>
        <View style={styles.iconWrap}>
          <ShieldCheckIcon
            size={16}
            color={activeColor}
            weight="duotone"
          />
        </View>
        <Text style={[styles.percentText, { color: colors.textPrimary }]}>
          {coveragePercent}%
        </Text>
        <Text style={[styles.statusText, { color: activeColor }]}>
          {isSafe ? "COVERED" : "DEFICIT"}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },
  centerContent: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
  },
  iconWrap: {
    marginBottom: 2,
  },
  percentText: {
    fontSize: 18,
    fontWeight: "800",
    letterSpacing: -0.5,
    fontVariant: ["tabular-nums"],
  },
  statusText: {
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.8,
    marginTop: 1,
  },
});
