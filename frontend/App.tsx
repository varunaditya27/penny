import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { Header } from "./src/components/Header";
import { DashboardScreen } from "./src/screens/DashboardScreen";
import { TrajectoryScreen } from "./src/screens/TrajectoryScreen";
import { AffordabilityScreen } from "./src/screens/AffordabilityScreen";
import { AgentChatScreen } from "./src/screens/AgentChatScreen";
import {
  CreditCard,
  Sparkle,
  TrendUp,
  Wallet,
} from "./src/components/icons";
import { colors } from "./src/theme/colors";

type NavigationTab = "dashboard" | "trajectory" | "affordability" | "chat";

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavigationTab>("dashboard");
  const [chatInitialQuery, setChatInitialQuery] = useState<string | undefined>();

  const getScreenTitle = () => {
    switch (currentTab) {
      case "dashboard":
        return {
          title: "Financial Overview",
          subtitle: "Available cash, upcoming bills, and emergency savings",
        };
      case "trajectory":
        return {
          title: "90-Day Forecast",
          subtitle: "Projected daily balance and upcoming bill schedule",
        };
      case "affordability":
        return {
          title: "Can I Afford It?",
          subtitle: "Check if a purchase fits your budget and future bills",
        };
      case "chat":
        return {
          title: "Ask Penny",
          subtitle: "Personal guidance for spending and budget decisions",
        };
    }
  };

  const navHeader = getScreenTitle();

  const handleNavigateToChat = (query?: string) => {
    setChatInitialQuery(query);
    setCurrentTab("chat");
  };

  const renderActiveScreen = () => {
    switch (currentTab) {
      case "dashboard":
        return <DashboardScreen onNavigate={(tab) => setCurrentTab(tab)} />;
      case "trajectory":
        return <TrajectoryScreen />;
      case "affordability":
        return (
          <AffordabilityScreen
            onNavigateToChat={handleNavigateToChat}
            onNavigateToTrajectory={() => setCurrentTab("trajectory")}
          />
        );
      case "chat":
        return <AgentChatScreen initialQuery={chatInitialQuery} />;
    }
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
        <StatusBar style="light" />
        <Header
          title={navHeader.title}
          subtitle={navHeader.subtitle}
          userId="user_01"
        />

        <View style={styles.contentContainer}>{renderActiveScreen()}</View>

        {/* Floating Frosted Glass Dock */}
        <View style={styles.dockWrapper}>
          <View style={styles.dockContainer}>
            {/* Tab 1: Dashboard / Liquidity */}
            <TouchableOpacity
              style={styles.dockItem}
              onPress={() => setCurrentTab("dashboard")}
              activeOpacity={0.7}
            >
              <Wallet
                size={22}
                color={
                  currentTab === "dashboard"
                    ? colors.emerald
                    : colors.textSecondary
                }
                weight={currentTab === "dashboard" ? "duotone" : "regular"}
              />
              <Text
                style={[
                  styles.dockLabel,
                  currentTab === "dashboard" && styles.dockLabelActive,
                ]}
              >
                Overview
              </Text>
            </TouchableOpacity>

            {/* Tab 2: Trajectory / Forecast */}
            <TouchableOpacity
              style={styles.dockItem}
              onPress={() => setCurrentTab("trajectory")}
              activeOpacity={0.7}
            >
              <TrendUp
                size={22}
                color={
                  currentTab === "trajectory"
                    ? colors.sky
                    : colors.textSecondary
                }
                weight={currentTab === "trajectory" ? "duotone" : "regular"}
              />
              <Text
                style={[
                  styles.dockLabel,
                  currentTab === "trajectory" && [
                    styles.dockLabelActive,
                    { color: colors.sky },
                  ],
                ]}
              >
                Forecast
              </Text>
            </TouchableOpacity>

            {/* Elevated Centerpiece Tab: Penny AI */}
            <TouchableOpacity
              style={styles.centerDockItem}
              onPress={() => setCurrentTab("chat")}
              activeOpacity={0.8}
            >
              <View
                style={[
                  styles.centerGlowRing,
                  currentTab === "chat" && styles.centerGlowRingActive,
                ]}
              >
                <View style={styles.centerButton}>
                  <Sparkle
                    size={24}
                    color={
                      currentTab === "chat" ? colors.black : colors.gold
                    }
                    weight="fill"
                  />
                </View>
              </View>
              <Text
                style={[
                  styles.dockLabel,
                  styles.centerLabel,
                  currentTab === "chat" && { color: colors.gold, fontWeight: "800" },
                ]}
              >
                Penny
              </Text>
            </TouchableOpacity>

            {/* Tab 4: Affordability */}
            <TouchableOpacity
              style={styles.dockItem}
              onPress={() => setCurrentTab("affordability")}
              activeOpacity={0.7}
            >
              <CreditCard
                size={22}
                color={
                  currentTab === "affordability"
                    ? colors.gold
                    : colors.textSecondary
                }
                weight={currentTab === "affordability" ? "duotone" : "regular"}
              />
              <Text
                style={[
                  styles.dockLabel,
                  currentTab === "affordability" && [
                    styles.dockLabelActive,
                    { color: colors.gold },
                  ],
                ]}
              >
                Afford
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  contentContainer: {
    flex: 1,
  },
  dockWrapper: {
    paddingHorizontal: 20,
    paddingBottom: 16,
    paddingTop: 8,
    backgroundColor: "transparent",
  },
  dockContainer: {
    flexDirection: "row",
    backgroundColor: "rgba(14, 20, 32, 0.94)",
    borderRadius: 28,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorderLight,
    justifyContent: "space-around",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.5,
    shadowRadius: 16,
    elevation: 8,
  },
  dockItem: {
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
    paddingVertical: 4,
  },
  dockLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: colors.textSecondary,
    marginTop: 4,
    letterSpacing: 0.2,
  },
  dockLabelActive: {
    color: colors.emerald,
    fontWeight: "700",
  },
  centerDockItem: {
    alignItems: "center",
    justifyContent: "center",
    flex: 1.2,
    marginTop: -16,
  },
  centerGlowRing: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorderActive,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 5,
  },
  centerGlowRingActive: {
    backgroundColor: colors.gold,
    borderColor: colors.white,
    shadowOpacity: 0.7,
    shadowRadius: 14,
  },
  centerButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "rgba(10, 14, 24, 0.85)",
    alignItems: "center",
    justifyContent: "center",
  },
  centerLabel: {
    marginTop: 2,
    fontSize: 10,
  },
});
