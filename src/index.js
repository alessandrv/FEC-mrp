import React from "react";
import ReactDOM from "react-dom";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import App from "./App";
import UnderStock from "./UnderStock";
import Inventory from "./Inventory";
import InventoryList from "./InventoryList";
import Dashboard from "./Dashboard";

ReactDOM.render(
  <Router>
    <Routes>
      <Route path="/" element={<InventoryList />} />
      <Route path="/understock" element={<UnderStock />} />
      <Route path="/dashboard" element={<Dashboard />} />

    </Routes>
  </Router>,
  document.getElementById("root")
);
