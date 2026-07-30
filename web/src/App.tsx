import { Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { SessionPage } from "./pages/SessionPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/buoi/:sid" element={<SessionPage />} />
    </Routes>
  );
}
