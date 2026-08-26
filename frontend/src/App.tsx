import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import GraphExplorer from './pages/GraphExplorer';
import SharedInsights from './pages/SharedInsights';
import Originality from './pages/Originality';
import ResearchGaps from './pages/ResearchGaps';
import SavedAnalyses from './pages/SavedAnalyses';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/graph" element={<GraphExplorer />} />
        <Route path="/shared" element={<SharedInsights />} />
        <Route path="/originality" element={<Originality />} />
        <Route path="/gaps" element={<ResearchGaps />} />
        <Route path="/saved" element={<SavedAnalyses />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
