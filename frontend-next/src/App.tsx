import { Navigate, Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import BrainstormList from "./pages/BrainstormList";
import BrainstormWorkspace from "./pages/BrainstormWorkspace";
import Dashboard from "./pages/Dashboard";
import StoryChat from "./pages/StoryChat";
import Characters from "./pages/Characters";
import CharacterWorkspace from "./pages/CharacterWorkspace";
import Family from "./pages/Family";
import RelationshipWeb from "./pages/RelationshipWeb";
import World from "./pages/World";
import WorldBible from "./pages/WorldBible";
import Story from "./pages/Story";
import StoryWorkshop from "./pages/StoryWorkshop";
import ImportNotes from "./pages/ImportNotes";
import ModulePage from "./pages/ModulePage";
import Search from "./pages/Search";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/brainstorm" element={<BrainstormList />} />
        <Route path="/brainstorm/:id" element={<BrainstormWorkspace />} />
        <Route path="/chat" element={<StoryChat />} />
        <Route path="/characters" element={<Characters />} />
        <Route
          path="/characters/:id/:section"
          element={<CharacterWorkspace />}
        />
        <Route path="/family" element={<Family />} />
        <Route path="/web" element={<RelationshipWeb />} />
        <Route path="/world-bible" element={<WorldBible />} />
        <Route path="/world" element={<World />} />
        <Route path="/story" element={<Story />} />
        <Route path="/story/:id/:tab" element={<StoryWorkshop />} />
        <Route path="/items" element={<ModulePage kind="items" />} />
        <Route path="/timeline" element={<ModulePage kind="timeline" />} />
        <Route path="/locations" element={<ModulePage kind="locations" />} />
        <Route
          path="/plot-threads"
          element={<ModulePage kind="plot-threads" />}
        />
        <Route
          path="/voice-profile"
          element={<ModulePage kind="voice-profile" />}
        />
        <Route
          path="/cross-reference"
          element={<ModulePage kind="cross-reference" />}
        />
        <Route
          path="/publication"
          element={<ModulePage kind="publication" />}
        />
        <Route path="/search" element={<Search />} />
        <Route path="/import" element={<ImportNotes />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Shell>
  );
}
