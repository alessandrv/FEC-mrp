// src/components/Dashboard.js

import React, { useEffect, useState } from "react";
import { Layout, Row, Col, Card, Spin, message, notification, DatePicker } from "antd";
import {
    DollarOutlined,
    StockOutlined,
    PieChartOutlined,
    FileTextOutlined,
    PlusOutlined,
    BoxPlotFilled
} from "@ant-design/icons";
import axios from "axios";
import TopArticleCard from "./components/TopArticleCard";
import AgentsTotalSalesPieChart from "./components/AgentsTotalSalesPieChart"; // Import the Pie Chart component
import AgentArticleSalesChart from "./components/AgentArticleSalesChart";
import ArticlesWithDescriptionBarChart from "./components/ArticlesWithDescriptionBarChart"; // Updated to Bar Chart
import UnderstockItemsTable from "./components/UnderstockItemsTable"; // Ensure this component exists
import useWebSocket from "./hooks/useWebSocket"; // Ensure this hook is correctly implemented
import dayjs from 'dayjs';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowTrendDown } from '@fortawesome/free-solid-svg-icons';
import { WarehouseOutlined } from "@mui/icons-material";
import FatturatoPerMeseChart from "./components/FatturatoPerMeseChart";
import SuppliersTable from "./components/SuppliersTable"; // Import the SuppliersTable component

const { Header, Content, Footer } = Layout;
const { RangePicker } = DatePicker;

const Dashboard = () => {
    // State variables for different metrics
    const [topArticle, setTopArticle] = useState([]);
    const [agentsTotalSales, setAgentsTotalSales] = useState([]);
    const [agentsTotalValue, setAgentsTotalValue] = useState([]);
    const [fatturatoTotale, setFatturatoTotale] = useState([]);

    const [agentArticleSales, setAgentArticleSales] = useState([]);
    const [articlesWithDescription, setArticlesWithDescription] = useState([]);
    const [lowStockCount, setLowStockCount] = useState(0);
    const [understockItems, setUnderstockItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [suppliers, setSuppliers] = useState([]); // Add state for suppliers

    const [inventoryDistribution, setInventoryDistribution] = useState([]);
     const [depositTotals, setDepositTotals] = useState([]);
    const [dateRange, setDateRange] = useState([
        dayjs().startOf('month'),
        dayjs()
    ]);

    // Handler for date range change
    const handleDateChange = (dates, dateStrings) => {
        if (dates) {
            setDateRange(dates);
            setLoading(true);
        }
    };

    // Fetch initial dashboard data with independent API calls
    useEffect(() => {
        const fetchTopArticle = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/top_article", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                setTopArticle(response.data);
            } catch (error) {
                message.error("Failed to fetch top article.");
                console.error("Top article fetch error:", error);
            }
        };

        const fetchAgentsTotalSales = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/agents_total_sales", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                const formattedData = response.data.map(agent => ({
                    ...agent,
                    total_occ_qmov: Number(agent.total_occ_qmov)
                }));
                setAgentsTotalSales(formattedData);
                console.log("Agents Total Sales Data:", formattedData);
            } catch (error) {
                message.error("Failed to fetch agents' total sales.");
                console.error("Agents total sales fetch error:", error);
            }
        };
        const fetchAgentsTotalValue = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/fatturato_per_agente", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                const formattedData = response.data.map(agent => ({
                    ...agent,
                    total_soldi: Number(agent.total_soldi)
                }));
                setAgentsTotalValue(formattedData);
                console.log("Agents Total Sales Data:", formattedData);
            } catch (error) {
                message.error("Failed to fetch agents' total sales.");
                console.error("Agents total sales fetch error:", error);
            }
        };
        const fetchTotalFatturato = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/fatturato_totale", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                
                setFatturatoTotale(response.data);
                console.log("Agents Total Sales Data:", response.data);
            } catch (error) {
                message.error("Failed to fetch fatturato totale.");
                console.error("Agents total sales fetch error:", error);
            }
        };
        const fetchDepositTotals = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/deposit_totals");
                setDepositTotals(response.data);
            } catch (error) {
                message.error("Failed to fetch deposit totals.");
                console.error("Deposit totals fetch error:", error);
            }
        };
        const fetchInventoryDistribution = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/inventory_distribution");
                setInventoryDistribution(response.data);
            } catch (error) {
                message.error("Failed to fetch inventory distribution.");
                console.error("Inventory distribution fetch error:", error);
            }
        };
        const fetchAgentArticleSales = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/agent_article_sales", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                setAgentArticleSales(response.data);
            } catch (error) {
                message.error("Failed to fetch agents' article sales.");
                console.error("Agent article sales fetch error:", error);
            }
        };

        const fetchArticlesWithDescription = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/top_article", { // Corrected endpoint
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                setArticlesWithDescription(response.data);
            } catch (error) {
                message.error("Failed to fetch articles with descriptions.");
                console.error("Articles with description fetch error:", error);
            }
        };

        const fetchLowStockCount = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/low_stock_count"); // Ensure this endpoint exists
                setLowStockCount(response.data.count);
            } catch (error) {
                message.error("Failed to fetch low stock count.");
                console.error("Low stock count fetch error:", error);
            }
        };

        const fetchUnderstockItems = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/understock_items"); // Ensure this endpoint exists
                setUnderstockItems(response.data);
            } catch (error) {
                message.error("Failed to fetch understock items.");
                console.error("Understock items fetch error:", error);
            }
        };

        const fetchSuppliers = async () => {
            try {
                const response = await axios.get("http://172.16.16.27:8000/suppliers", {
                    params: {
                        start_date: dateRange[0].format('DD-MM-YYYY'),
                        end_date: dateRange[1].format('DD-MM-YYYY')
                    }
                });
                setSuppliers(response.data);
            } catch (error) {
                message.error("Failed to fetch suppliers.");
                console.error("Suppliers fetch error:", error);
            }
        };

        // Execute all fetch functions
        const fetchData = async () => {
            await Promise.all([
                fetchTopArticle(),
                fetchAgentsTotalSales(),
                fetchAgentsTotalValue(),
                fetchTotalFatturato(),
                fetchAgentArticleSales(),
                fetchArticlesWithDescription(),
                fetchDepositTotals(),
                fetchSuppliers(), // Add fetchSuppliers to the fetchData
            ]);
            setLoading(false);
        };

       

        fetchData();
    }, [dateRange]);

    // Handle real-time updates via WebSocket
    const handleWebSocketMessage = (event) => {
        try {
            const updatedData = JSON.parse(event.data);
            // Update top_article
            if (updatedData.top_article) {
                setTopArticle(updatedData.top_article);
            }
            // Update agents_total_sales
            if (updatedData.agents_total_sales) {
                setAgentsTotalSales(updatedData.agents_total_sales);
            }
            // Update agent_article_sales
            if (updatedData.agent_article_sales) {
                setAgentArticleSales(updatedData.agent_article_sales);
            }
            // Update articles_with_description
            if (updatedData.articles_with_description) {
                setArticlesWithDescription(updatedData.articles_with_description);
            }
            // Update low_stock_count
            if (updatedData.low_stock_count) {
                setLowStockCount(updatedData.low_stock_count);
            }
            // Update understock_items
            if (updatedData.understock_items) {
                setUnderstockItems(updatedData.understock_items);
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
        "ws://172.16.16.27:8000/ws/articles", // Ensure this WebSocket endpoint exists and sends appropriate data
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
    const totalInventory = depositTotals.reduce((acc, depot) => acc + depot.total_deposit, 0);


    return (
        <Layout style={{ minHeight: "100vh" }}>
            <div style={{ background: "#fff", padding: "20px", textAlign: "center", fontSize: "24px", zIndex:3 }}>
                Inventory Dashboard
                <div style={{  }}>
                    <RangePicker
                        value={dateRange} // Controlled component
                        onChange={handleDateChange}
                        format="DD-MM-YYYY"
                        allowClear={false} // Optional: prevent clearing the range
                        style={{ width: "50%" }} // Optional: adjust width as needed
                    />
                </div>
            </div>
            <Content style={{ margin: "20px" }}>
            <Row gutter={[16, 16]}>
                    {/* KPI Cards */}
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Card.Meta
                                avatar={<WarehouseOutlined style={{ fontSize: "32px", color: "#1890ff" }} />}
                                title="Inventario totale"
                                description={`${totalInventory.toLocaleString()}`}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Card.Meta
avatar={<FontAwesomeIcon  style={{ fontSize: "32px", color: "red" }} icon={faArrowTrendDown} />}
                                title="Oggetti sotto scorta"
                                description={lowStockCount}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                        <Card>
                            <Card.Meta
                                avatar={<DollarOutlined style={{ fontSize: "32px", color: "green" }} />}
                                title="Fatturato"
                                description={`${fatturatoTotale[0].total_soldi} €`}
                            />
                        </Card>
                    </Col>
                    {/* Removed Duplicate "Top Articles" Card */}
                    {/* Add more KPI Cards as needed */}
                </Row>
                <Row gutter={[16, 16]} style={{ marginTop: "20px" }}>
                    {/* Top Performant Article */}
                  
                    <Col xs={12}>
                    <Card title="Top 20 articoli">

                        <ArticlesWithDescriptionBarChart data={articlesWithDescription} />
                        </Card>
                    </Col>
                 
                    {/* Total Sold by Each Agent as Pie Chart */}
                    <Col xs={24} md={12}>
                        <Card title="Prestazioni Agenti">
                            <AgentsTotalSalesPieChart dataVendite={agentsTotalSales} dataFatturato={agentsTotalValue} />
                        </Card>
                    </Col>
                   
                </Row>
                <Row gutter={[16, 16]} style={{ marginTop: "20px" }}>

                {/* Total Sold for Each Article per Agent */}
               
                <Col xs={12}>
                    <Card title="Storico fatturato">

                        <FatturatoPerMeseChart/>
                        </Card>
                    </Col>
                    
                {/* ... [Existing Rows and Cards] */}

                {/* New Suppliers Table Card */}
                    <Col xs={12}>
                        <Card title="Fornitori">
                            <SuppliersTable dateRange={dateRange} />
                        </Card>
                    </Col>
                    </Row>
                {/* ... [Existing Rows and Cards] */}
          
                {/* Existing Components */}
                <Row gutter={[16, 16]} style={{ marginTop: "20px" }}>
                    <Col xs={24} md={12}>
                        <Card title="Understock Items">
                            <UnderstockItemsTable data={understockItems} />
                        </Card>
                    </Col>
                    <Col xs={24} md={12}>
                        <Card title="Low Stock Count">
                            <p>{lowStockCount}</p>
                        </Card>
                    </Col>
                </Row>

                {/* Additional Charts or Components can be added here */}
            </Content>
            <Footer style={{ textAlign: "center" }}>©2024 FEC Italia</Footer>
        </Layout>
    );

};

export default Dashboard;
