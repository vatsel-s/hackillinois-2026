import { useState, useCallback } from "react";
import Opener from "./pages/Opener";
import MainSite from "./pages/MainSite";

export default function App() {
  const [showMain, setShowMain]     = useState(false);
  const [mainVisible, setMainVisible] = useState(false);

  const handleComplete = useCallback(() => {
    setShowMain(true);
    // Double rAF ensures the element is mounted before the fade starts
    requestAnimationFrame(() =>
      requestAnimationFrame(() => setMainVisible(true))
    );
  }, []);

  return (
    <>
      {/* Opener stays mounted only until onComplete fires */}
      {!showMain && <Opener onComplete={handleComplete} />}

      {/* Main site fades in after opener finishes */}
      {showMain && (
        <div
          style={{
            opacity:    mainVisible ? 1 : 0,
            transition: "opacity 0.7s ease",
          }}
        >
          <MainSite />
        </div>
      )}
    </>
  );
}