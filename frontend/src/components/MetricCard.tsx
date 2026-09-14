import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors } from "../theme/colors";

interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  icon?: string;
  badgeText?: string;
  variant?: "default" | "success" | "warning" | "danger" | "accent";
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  icon,
  badgeText,
  variant = "default",
}) => {
  const getBorderColor = () => {
    switch (variant) {
      case "success":
        return colors.success;
      case "warning":
        return colors.warning;
      case "danger":
        return colors.danger;
      case "accent":
        return colors.accent;
      default:
        return colors.surfaceBorder;
    }
  };

  const getBadgeStyle = () => {
    switch (variant) {
      case "success":
        return { backgroundColor: colors.successLight, color: colors.success };
      case "warning":
        return { backgroundColor: colors.warningLight, color: colors.warning };
      case "danger":
        return { backgroundColor: colors.dangerLight, color: colors.danger };
      case "accent":
        return { backgroundColor: colors.accentLight, color: colors.accent };
      default:
        return { backgroundColor: colors.surfaceLight, color: colors.textSecondary };
    }
  };

  const badgeTheme = getBadgeStyle();

  return (
    <View style={[styles.card, { borderLeftColor: getBorderColor(), borderLeftWidth: 4 }]}>
      <View style={styles.topRow}>
        <View style={styles.labelContainer}>
          {icon ? <Text style={styles.icon}>{icon}</Text> : null}
          <Text style={styles.label}>{label}</Text>
        </View>
        {badgeText ? (
          <View style={[styles.badge, { backgroundColor: badgeTheme.backgroundColor }]}>
            <Text style={[styles.badgeText, { color: badgeTheme.color }]}>
              {badgeText}
            </Text>
          </View>
        ) : null}
      </View>
      <Text style={styles.value}>{value}</Text>
      {subValue ? <Text style={styles.subValue}>{subValue}</Text> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 2,
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  labelContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  icon: {
    fontSize: 14,
    marginRight: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  value: {
    fontSize: 26,
    fontWeight: "800",
    color: colors.textPrimary,
    letterSpacing: 0.5,
  },
  subValue: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 4,
  },
});
