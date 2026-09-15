import React, { Component, ErrorInfo, ReactNode } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors } from "../theme/colors";
import { WarningCircle } from "./icons";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an uncaught component error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <View style={styles.card}>
            <View style={styles.iconCircle}>
              <WarningCircle size={28} color={colors.gold} weight="duotone" />
            </View>
            <Text style={styles.title}>
              {this.props.fallbackTitle || "Something went wrong"}
            </Text>
            <Text style={styles.message}>
              {this.props.fallbackMessage ||
                "An unexpected issue occurred while rendering this screen. Your account data remains safe."}
            </Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={this.handleReset}
              activeOpacity={0.8}
            >
              <Text style={styles.retryButtonText}>Reload View</Text>
            </TouchableOpacity>
          </View>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  card: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 20,
    padding: 24,
    width: "100%",
    maxWidth: 380,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 6,
  },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.goldLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
  },
  title: {
    fontSize: 17,
    fontWeight: "800",
    color: colors.textPrimary,
    marginBottom: 8,
    textAlign: "center",
  },
  message: {
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    textAlign: "center",
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: colors.gold,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 24,
    alignItems: "center",
  },
  retryButtonText: {
    fontSize: 13,
    fontWeight: "800",
    color: colors.black,
  },
});
