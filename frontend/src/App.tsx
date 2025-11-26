import { Routes, Route } from "react-router-dom";
import PlannerPage from "./pages/PlannerPage";
import Layout from "./components/Layout";

function App() {
  return (
    <div className="app-shell">
      <Layout>
        <Routes>
          <Route path="/" element={<PlannerPage />} />
        </Routes>
      </Layout>
    </div>
  );
}

export default App;
