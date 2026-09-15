import { Platform, TextStyle } from "react-native";

export const fontSans: TextStyle = {
  fontFamily: Platform.select({
    android: "sans-serif",
    ios: "System",
    default: "sans-serif",
  }),
};

export const fontSansMedium: TextStyle = {
  fontFamily: Platform.select({
    android: "sans-serif-medium",
    ios: "System",
    default: "sans-serif",
  }),
};
