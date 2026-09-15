import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors } from "../theme/colors";
import { fontSans } from "../theme/typography";

export interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  icon?: React.ReactNode;
  badgeText?: string;
  variant?: "default" | "success" | "warning" | "danger" | "accent" | "gold";
}

const MetricCardComponent: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  icon,
  badgeText,
  variant = "default",
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case "success":
        return {
          badgeBg: colors.emeraldLight,
          badgeColor: colors.emerald,
          dotColor: colors.emerald,
          borderColor: colors.surfaceBorderEmerald,
        };
      case "warning":
      case "gold":
        return {
          badgeBg: colors.goldLight,
          badgeColor: colors.gold,
          dotColor: colors.gold,
          borderColor: colors.surfaceBorderActive,
        };
      case "danger":
        return {
          badgeBg: colors.dangerLight,
          badgeColor: colors.danger,
          dotColor: colors.danger,
          borderColor: colors.dangerLight,
        };
      case "accent":
        return {
          badgeBg: colors.violetLight,
          badgeColor: colors.violet,
          dotColor: colors.violet,
          borderColor: colors.violetLight,
        };
      default:
        return {
          badgeBg: colors.surfaceLight,
          badgeColor: colors.textSecondary,
          dotColor: colors.textDim,
          borderColor: colors.surfaceBorder,
        };
    }
  };

  const vStyles = getVariantStyles();

  return (
    <View style={[styles.card, { borderColor: vStyles.borderColor }]}>
      <View style={styles.topRow}>
        <View style={styles.labelContainer}>
          {icon ? <View style={styles.iconContainer}>{icon}</View> : null}
          <Text style={styles.label} numberOfLines={1}>
            {label}
          </Text>
        </View>
        {badgeText ? (
          <View style={[styles.badge, { backgroundColor: vStyles.badgeBg }]}>
            <Text style={[styles.badgeText, { color: vStyles.badgeColor }]}>
              {badgeText}
            </Text>
          </View>
        ) : (
          <View style={[styles.statusDot, { backgroundColor: vStyles.dotColor }]} />
        )}
      </View>
      <Text style={styles.value} numberOfLines={1}>
        {value}
      </Text>
      {subValue ? (
        <Text style={styles.subValue} numberOfLines={2}>
          {subValue}
        </Text>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 3,
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  labelContainer: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },
  iconContainer: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: colors.surfaceLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  label: {
    ...fontSans,
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    flex: 1,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  badgeText: {
    ...fontSans,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  value: {
    ...fontSans,
    fontSize: 22,
    fontWeight: "800",
    color: colors.textPrimary,
    letterSpacing: -0.5,
    fontVariant: ["tabular-nums"],
  },
  subValue: {
    ...fontSans,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 4,
    lineHeight: 16,
  },
});

export const MetricCard = React.memo(MetricCardComponent);

