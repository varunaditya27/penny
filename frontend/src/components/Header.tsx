import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors } from "../theme/colors";
import { fontSans } from "../theme/typography";
import { PennyLogo } from "./PennyLogo";
import { SparkleIcon } from "./icons";

interface HeaderProps {
  title: string;
  subtitle?: string;
  userId?: string;
}

const HeaderComponent: React.FC<HeaderProps> = ({
  title,
  subtitle,
  userId = "user_01",
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.leftCol}>
        <View style={styles.brandRow}>
          <View style={styles.logoBadge}>
            <PennyLogo size={22} showTrajectory={false} />
          </View>
          <Text style={styles.brandName}>PENNY</Text>
          <View style={styles.liveTag}>
            <View style={styles.liveDot} />
            <SparkleIcon size={10} color={colors.emerald} />
            <Text style={styles.liveText}>ACTIVE</Text>
          </View>
        </View>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>

      <View style={styles.userBadge}>
        <View style={styles.userDot} />
        <Text style={styles.userText}>{userId.toUpperCase()}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceBorder,
  },
  leftCol: {
    flex: 1,
    paddingRight: 12,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },
  logoBadge: {
    width: 26,
    height: 26,
    borderRadius: 7,
    backgroundColor: colors.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorderLight,
  },
  brandName: {
    ...fontSans,
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 2,
    color: colors.gold,
    marginRight: 10,
  },
  liveTag: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.emeraldLight,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.surfaceBorderEmerald,
    gap: 4,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.emerald,
  },
  liveText: {
    ...fontSans,
    fontSize: 9,
    fontWeight: "800",
    color: colors.emerald,
    letterSpacing: 0.6,
  },
  title: {
    ...fontSans,
    fontSize: 21,
    fontWeight: "800",
    color: colors.textPrimary,
    letterSpacing: -0.3,
  },
  subtitle: {
    ...fontSans,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 16,
  },
  userBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceCard,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginTop: 4,
    gap: 6,
  },
  userDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  userText: {
    ...fontSans,
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 0.8,
  },
});

export const Header = React.memo(HeaderComponent);

