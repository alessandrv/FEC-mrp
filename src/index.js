import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import App from "./App";
import UnderStock from "./UnderStock";
import Inventory from "./Inventory";
import InventoryList from "./InventoryList";
import Dashboard from "./Dashboard";
import ProductsAvailabilityTabs from "./ProductsAvailabilityTabs";
import PriceList from "./PriceList";

const container = document.getElementById("root");
const root = createRoot(container);

root.render(
  <Router>
    <Routes>
      <Route path="/" element={<InventoryList />} />
      <Route path="/understock" element={<UnderStock />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/availability" element={<ProductsAvailabilityTabs />} />
      <Route path="/pricelist" element={<PriceList />} />
    </Routes>
  </Router>
);
