import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import {
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Header } from "./src/components/Header";
import { DashboardScreen } from "./src/screens/DashboardScreen";
import { TrajectoryScreen } from "./src/screens/TrajectoryScreen";
import { AffordabilityScreen } from "./src/screens/AffordabilityScreen";
import { AgentChatScreen } from "./src/screens/AgentChatScreen";
import { colors } from "./src/theme/colors";

type NavigationTab = "dashboard" | "trajectory" | "affordability" | "chat";

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavigationTab>("dashboard");
  const [chatInitialQuery, setChatInitialQuery] = useState<string | undefined>();

  const getScreenTitle = () => {
    switch (currentTab) {
      case "dashboard":
        return { title: "Financial Overview", subtitle: "Real-time liquidity and reserve buffer" };
      case "trajectory":
        return { title: "90-Day Trajectory", subtitle: "Dynamic balance simulation and dip analysis" };
      case "affordability":
        return { title: "Affordability Engine", subtitle: "Invariants check & payment plan optimizer" };
      case "chat":
        return { title: "Penny AI Assistant", subtitle: "Multi-agent financial reasoning brain" };
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
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <Header
        title={navHeader.title}
        subtitle={navHeader.subtitle}
        userId="user_01"
      />

      <View style={styles.contentContainer}>{renderActiveScreen()}</View>

      {/* Bottom Navigation Bar */}
      <View style={styles.navBar}>
        <TouchableOpacity
          style={styles.navItem}
          onPress={() => setCurrentTab("dashboard")}
          activeOpacity={0.7}
        >
          <Text style={[styles.navIcon, currentTab === "dashboard" && styles.navIconActive]}>
            📊
          </Text>
          <Text style={[styles.navLabel, currentTab === "dashboard" && styles.navLabelActive]}>
            Dashboard
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.navItem}
          onPress={() => setCurrentTab("trajectory")}
          activeOpacity={0.7}
        >
          <Text style={[styles.navIcon, currentTab === "trajectory" && styles.navIconActive]}>
            📈
          </Text>
          <Text style={[styles.navLabel, currentTab === "trajectory" && styles.navLabelActive]}>
            Trajectory
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.navItem}
          onPress={() => setCurrentTab("affordability")}
          activeOpacity={0.7}
        >
          <Text style={[styles.navIcon, currentTab === "affordability" && styles.navIconActive]}>
            💳
          </Text>
          <Text style={[styles.navLabel, currentTab === "affordability" && styles.navLabelActive]}>
            Afford
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.navItem}
          onPress={() => setCurrentTab("chat")}
          activeOpacity={0.7}
        >
          <View style={styles.chatIconWrap}>
            <Text style={[styles.navIcon, currentTab === "chat" && styles.navIconActive]}>
              💬
            </Text>
            <View style={styles.aiBadgeDot} />
          </View>
          <Text style={[styles.navLabel, currentTab === "chat" && styles.navLabelActive]}>
            Penny AI
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
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
  navBar: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    paddingVertical: 10,
    paddingBottom: 14,
    justifyContent: "space-around",
    alignItems: "center",
  },
  navItem: {
    alignItems: "center",
    flex: 1,
  },
  navIcon: {
    fontSize: 20,
    marginBottom: 3,
    opacity: 0.6,
  },
  navIconActive: {
    opacity: 1,
    transform: [{ scale: 1.1 }],
  },
  navLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  navLabelActive: {
    color: colors.primary,
    fontWeight: "700",
  },
  chatIconWrap: {
    position: "relative",
  },
  aiBadgeDot: {
    position: "absolute",
    top: -2,
    right: -4,
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: colors.accent,
  },
});
