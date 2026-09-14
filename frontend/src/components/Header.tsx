import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors } from "../theme/colors";

interface HeaderProps {
  title: string;
  subtitle?: string;
  userId?: string;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  userId = "user_01",
}) => {
  return (
    <View style={styles.container}>
      <View>
        <View style={styles.brandRow}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoText}>🪙</Text>
          </View>
          <Text style={styles.brandName}>PENNY</Text>
          <View style={styles.liveTag}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>AI ACTIVE</Text>
          </View>
        </View>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      <View style={styles.userBadge}>
        <Text style={styles.userText}>{userId.toUpperCase()}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },
  logoBadge: {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: colors.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
  },
  logoText: {
    fontSize: 14,
  },
  brandName: {
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 1.5,
    color: colors.primary,
    marginRight: 10,
  },
  liveTag: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(16, 185, 129, 0.12)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(16, 185, 129, 0.3)",
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.success,
    marginRight: 5,
  },
  liveText: {
    fontSize: 9,
    fontWeight: "700",
    color: colors.success,
    letterSpacing: 0.5,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  userBadge: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginTop: 4,
  },
  userText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 0.5,
  },
});
