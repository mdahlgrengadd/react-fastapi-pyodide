// filepath: d:\react-router-fastapi\src\lib\react-router-fastapi\router\hooks.ts
import { useContext } from "react";

import { FastAPIRouterContext, FastAPIRouterContextType } from "./context";

export const useFastAPIRouter = (): FastAPIRouterContextType => {
  const context = useContext(FastAPIRouterContext);
  if (!context) {
    throw new Error("useFastAPIRouter must be used within a FastAPIRouter");
  }
  return context;
};
