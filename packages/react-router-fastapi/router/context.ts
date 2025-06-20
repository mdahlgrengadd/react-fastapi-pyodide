// filepath: d:\react-router-fastapi\src\lib\react-router-fastapi\router\context.ts
import { createContext } from "react";

import { FastAPIRouterProps } from "./types";

export interface FastAPIRouterContextType {
  apiBaseURL: string;
  authConfig?: FastAPIRouterProps["authConfig"];
  isDevMode: boolean;
}

export const FastAPIRouterContext =
  createContext<FastAPIRouterContextType | null>(null);
