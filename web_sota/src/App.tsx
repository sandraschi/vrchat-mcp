import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';

import { Dashboard } from '@/pages/dashboard';
import { Avatars } from '@/pages/avatars';
import { OSC } from '@/pages/osc';
import { Docs } from '@/pages/docs';
import { Settings } from '@/pages/settings';
import { Tools } from '@/pages/tools';
import { Status } from '@/pages/status';
import { Apps } from '@/pages/apps';
import { Help } from '@/pages/help';

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
  )
}

export default App
