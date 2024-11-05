// src/components/Dashboard.js

import React, { useEffect, useState } from "react";
import { Layout, Row, Col, Card, Spin, message, notification } from "antd";
import {
    DollarOutlined,
    StockOutlined,
    PieChartOutlined,
    FileTextOutlined,
    PlusOutlined
} from "@ant-design/icons";
import axios from "axios";
import RechartsLineChart from "./components/RechartsLineChart";
import RechartsPieChart from "./components/RechartsPieChart";
import DepositBarChart from "./components/DepositBarChart";
import RechartsParetoChart from "./components/RechartsParetoChart";
import UnderstockItemsTable from "./components/UnderstockItemsTable"; // Import the UnderstockItemsTable component
import useWebSocket from "./hooks/useWebSocket"; // Import your WebSocket hook

const { Header, Content, Footer } = Layout;

const Dashboard = () => {
    // State variables for different metrics
    const [depositTotals, setDepositTotals] = useState([]);
    const [topArticles, setTopArticles] = useState([]);
    const [lowStockCount, setLowStockCount] = useState(0);
    const [understockItems, setUnderstockItems] = useState([]);
    const [inventoryDistribution, setInventoryDistribution] = useState([]);
    const [loading, setLoading] = useState(true);

    // Fetch initial dashboard data with independent API calls
    useEffect(() => {
        const fetchDepositTotals = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/deposit_totals");
                setDepositTotals(response.data);
            } catch (error) {
                message.error("Failed to fetch deposit totals.");
                console.error("Deposit totals fetch error:", error);
            }
        };

        const fetchTopArticles = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/top_articles", { params: { limit: 5 } });
                setTopArticles(response.data);
            } catch (error) {
                message.error("Failed to fetch top articles.");
                console.error("Top articles fetch error:", error);
            }
        };

        const fetchLowStockCount = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/low_stock_count");
                setLowStockCount(response.data.count);
            } catch (error) {
                message.error("Failed to fetch low stock count.");
                console.error("Low stock count fetch error:", error);
            }
        };

        const fetchUnderstockItems = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/understock_items");
                setUnderstockItems(response.data);
            } catch (error) {
                message.error("Failed to fetch understock items.");
                console.error("Understock items fetch error:", error);
            }
        };

        const fetchInventoryDistribution = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/inventory_distribution");
                setInventoryDistribution(response.data);
            } catch (error) {
                message.error("Failed to fetch inventory distribution.");
                console.error("Inventory distribution fetch error:", error);
            }
        };

        // Execute all fetch functions
        const fetchData = async () => {
            await Promise.all([
                fetchDepositTotals(),
                fetchTopArticles(),
                fetchLowStockCount(),
                fetchUnderstockItems(),
                fetchInventoryDistribution()
            ]);
            setLoading(false);
        };

        fetchData();
    }, []);

    // Handle real-time updates via WebSocket
    const handleWebSocketMessage = (event) => {
        try {
            const updatedData = JSON.parse(event.data);
            // Update deposit_totals
            if (updatedData.deposit_totals) {
                setDepositTotals(updatedData.deposit_totals);
            }
            // Update top_articles
            if (updatedData.top_articles) {
                setTopArticles(updatedData.top_articles);
            }
            // Update low_stock_count
            if (updatedData.low_stock_count) {
                setLowStockCount(updatedData.low_stock_count);
            }
            // Update understock_items
            if (updatedData.understock_items) {
                setUnderstockItems(updatedData.understock_items);
            }
            // Update inventory_distribution
            if (updatedData.inventory_distribution) {
                setInventoryDistribution(updatedData.inventory_distribution);
            }

            // Trigger notification if low_stock_count increases
            if (updatedData.low_stock_count && updatedData.low_stock_count > lowStockCount) {
                notification.warning({
                    message: 'Low Stock Alert',
                    description: `There are now ${updatedData.low_stock_count} items with low stock levels.`,
                    placement: 'topRight',
                });
            }
        } catch (error) {
            console.error("Error parsing WebSocket message:", error);
        }
    };

    // Initialize WebSocket connection
    useWebSocket(
        "ws://172.16.16.69:8000/ws/articles",
        handleWebSocketMessage,
        () => console.log("WebSocket connection opened."),
        () => console.log("WebSocket connection closed."),
        (error) => console.error("WebSocket error:", error)
    );

    if (loading) {
        return (
            <Spin tip="Loading Dashboard..." style={{ width: "100%", marginTop: "20%" }} />
        );
    }

    // Calculate Total Inventory from depositTotals
    const totalInventory = depositTotals.reduce((acc, depot) => acc + depot.total_deposit, 0);

    return (
        <Layout style={{ minHeight: "100vh" }}>
            <Header style={{ background: "#fff", padding: 0, textAlign: "center", fontSize: "24px" }}>
                Inventory Dashboard
            </Header>
            <Content style={{ margin: "20px" }}>
                <Row gutter={[16, 16]}>
                    {/* KPI Cards */}
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Card.Meta
                                avatar={<DollarOutlined style={{ fontSize: "32px", color: "#1890ff" }} />}
                                title="Total Inventory"
                                description={`$${totalInventory.toLocaleString()}`}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Card.Meta
                                avatar={<StockOutlined style={{ fontSize: "32px", color: "#52c41a" }} />}
                                title="Low Stock Items"
                                description={lowStockCount}
                            />
                        </Card>
                    </Col>
                    {/* Removed Duplicate "Top Articles" Card */}
                    {/* Add more KPI Cards as needed */}
                </Row>

                

                {/* Deposits Bar Chart and Understock Items Table */}
                <Row gutter={[16, 16]} style={{ marginTop: "20px" }}>
                    <Col xs={24} md={12}>
                        <Card title="Total Deposits">
                            <DepositBarChart data={depositTotals} />
                        </Card>
                    </Col>
                    <Col xs={24} md={12}>
                        <Card  title="Understock Items">
                            <UnderstockItemsTable data={understockItems} />
                        </Card>
                    </Col>
                </Row>

                {/* Pie Chart and Quick Access Links */}
                <Row gutter={[16, 16]} style={{ marginTop: "20px" }}>
                    <Col xs={24} md={12}>
                        <Card title="Inventory Distribution">
                            <RechartsPieChart data={inventoryDistribution} />
                        </Card>
                    </Col>
                    <Col xs={24} md={12}>
                        <Card title="Quick Access" style={{ textAlign: "center" }}>
                            <Row gutter={[16, 16]}>
                                <Col span={12}>
                                    <Card
                                        hoverable
                                        style={{ textAlign: "center" }}
                                        onClick={() => window.location.href = "/reports"}
                                        bodyStyle={{ padding: "20px" }}
                                    >
                                        <FileTextOutlined style={{ fontSize: "48px", color: "#1890ff" }} />
                                        <p>Reports</p>
                                    </Card>
                                </Col>
                                <Col span={12}>
                                    <Card
                                        hoverable
                                        style={{ textAlign: "center" }}
                                        onClick={() => window.location.href = "/new-orders"}
                                        bodyStyle={{ padding: "20px" }}
                                    >
                                        <PlusOutlined style={{ fontSize: "48px", color: "#52c41a" }} />
                                        <p>New Orders</p>
                                    </Card>
                                </Col>
                            </Row>
                        </Card>
                    </Col>
                </Row>
            </Content>
            <Footer style={{ textAlign: "center" }}>©2024 Your Company</Footer>
        </Layout>
    );

};

export default Dashboard;
