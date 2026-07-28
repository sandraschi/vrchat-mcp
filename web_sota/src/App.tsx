import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { Apps } from "@/pages/apps";
import { Avatars } from "@/pages/avatars";
import { Dashboard } from "@/pages/dashboard";
import { Docs } from "@/pages/docs";
import { Help } from "@/pages/help";
import { OSC } from "@/pages/osc";
import { Settings } from "@/pages/settings";
import { Status } from "@/pages/status";
import { Tools } from "@/pages/tools";

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/avatars" element={<Avatars />} />
          <Route path="/osc" element={<OSC />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/status" element={<Status />} />
          <Route path="/apps" element={<Apps />} />
          <Route path="/help" element={<Help />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
