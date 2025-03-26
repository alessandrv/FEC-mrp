import React, { useEffect, useState } from "react";
import axios from "axios";
import {
    Table,
    Spin,
    message,
    Modal,
    Checkbox,
    Dropdown,
    Menu,
    Input,
    Tag,
    Radio,
    Tooltip as AntTooltip,
    Button,
    Switch,
    Typography,
    Alert,
    Select,
} from "antd";
import { CheckOutlined, CloseOutlined, EllipsisOutlined, LoadingOutlined, MenuFoldOutlined, SearchOutlined } from "@ant-design/icons";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
} from "recharts";
import "./InventoryList.css"; // Custom CSS file for styling
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import useWebSocket from "./hooks/useWebSocket"; // Import the custom hook
import { API_BASE_URL, WEBSOCKET_URL } from './config'; // Import configuration

const ArticlesTable = () => {
    const [contextMenuVisible, setContextMenuVisible] = useState(false);
    const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
    const [currentRow, setCurrentRow] = useState(null);
    const [contextMenuOptions, setContextMenuOptions] = useState([]);
    // Add this line with your other useState hooks
    const [hideZeroRows, setHideZeroRows] = useState(true);
    // Add these state variables with your other useState hooks
    const [hoveredRowKey, setHoveredRowKey] = useState(null);
    const [highlightedColumns, setHighlightedColumns] = useState([]);

    // Data and Loading States
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    // Modal for Price History
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [chartLoading, setChartLoading] = useState(false);
    const [chartData, setChartData] = useState([]);
    const [modalTitle, setModalTitle] = useState("");
    const [maxPriceData, setMaxPriceData] = useState(null);
    const [minPriceData, setMinPriceData] = useState(null);
    const [isAverage, setIsAverage] = useState(false);
    const [rawChartData, setRawChartData] = useState([]);
    const [averageChartData, setAverageChartData] = useState([]);
    const [valuta, setValuta] = useState(null);

    // Modal for Order History
    const [isOrderHistoryModalVisible, setIsOrderHistoryModalVisible] = useState(false);
    const [orderHistoryData, setOrderHistoryData] = useState([]);
    const [orderHistoryLoading, setOrderHistoryLoading] = useState(false);
    const [orderHistoryModalTitle, setOrderHistoryModalTitle] = useState("");

    // Modal for Today's Orders
    const [isTodayOrdersModalVisible, setIsTodayOrdersModalVisible] = useState(false);
    const [todayOrdersData, setTodayOrdersData] = useState([]);
    const [todayOrdersLoading, setTodayOrdersLoading] = useState(false);
    const [todayOrdersModalTitle, setTodayOrdersModalTitle] = useState("");

    // Filters and Search States
    const [showNegativeOnly, setShowNegativeOnly] = useState(false);
    const [showUnderScortaOnly, setShowUnderScortaOnly] = useState(false);
    const [searchText, setSearchText] = useState("");
    const [apFilter, setApFilter] = useState("A");

    // Add these new state variables at the beginning of the component
    const [isSimulationModalVisible, setIsSimulationModalVisible] = useState(false);
    const [simulationRows, setSimulationRows] = useState([{ code: '', quantity: '' }]);
    const [selectedTimePeriod, setSelectedTimePeriod] = useState('today');

    // Add these additional state variables for simulation results
    const [simulationResults, setSimulationResults] = useState([]);
    const [simulationLoading, setSimulationLoading] = useState(false);
    const [simulationComplete, setSimulationComplete] = useState(false);

    // Add these new state variables for the Kiosk modal
    const [isKioskModalVisible, setIsKioskModalVisible] = useState(false);
    const [kioskData, setKioskData] = useState([]);
    const [selectedKiosk, setSelectedKiosk] = useState('Kiosk');

    // Add the filter state for Kiosk modal
    const [kioskFilter, setKioskFilter] = useState('');

    const handleWebSocketMessage = (event) => {
        try {
            const updatedData = JSON.parse(event.data);
            const parsedData = parseIntegerData(updatedData);

            // Sort the data based on 'c_articolo'
            parsedData.sort((a, b) => a.c_articolo.localeCompare(b.c_articolo));

            setData(parsedData);
            console.log('Data updated via WebSocket.');
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    // Initialize WebSocket connection with environment variable
    useWebSocket(
        `${WEBSOCKET_URL}/ws/articles`,
        handleWebSocketMessage,
        () => console.log('WebSocket connection opened.'),
        () => console.log('WebSocket connection closed.'),
        (error) => console.error('WebSocket error:', error)
    );

    // Fetch data from the FastAPI backend
    // Function to convert relevant values to integers, if needed
    // Function to convert relevant fields to integers
    const parseIntegerData = (data) => {
        return data.map((item) => ({
            ...item,
            c_articolo: item.c_articolo, // Articolo can remain as a string
            a_p: item.a_p, // AP might also remain as a string
            d_articolo: item.d_articolo, // Descrizione as a string
            lt: parseInt(item.lt) || 0,
            scrt: parseInt(item.scrt) || 0,
            giac_d01: parseInt(item.giac_d01) || 0,
            giac_d20: parseInt(item.giac_d20) || 0,
            giac_d32: parseInt(item.giac_d32) || 0,
            giac_d40: parseInt(item.giac_d40) || 0,
            giac_d48: parseInt(item.giac_d48) || 0,
            giac_d60: parseInt(item.giac_d60) || 0,
            giac_d81: parseInt(item.giac_d81) || 0,
            ord_mpp: parseInt(item.ord_mpp) || 0,
            ord_mp: parseInt(item.ord_mp) || 0,
            ord_mc: parseInt(item.ord_mc) || 0,
            dom_mc: parseInt(item.dom_mc) || 0,
            dom_ms: parseInt(item.dom_ms) || 0,
            dom_msa: parseInt(item.dom_msa) || 0,
            dom_mss: parseInt(item.dom_mss) || 0,
            off_mc: parseInt(item.off_mc) || 0,
            off_ms: parseInt(item.off_ms) || 0,
            off_msa: parseInt(item.off_msa) || 0,
            off_mss: parseInt(item.off_mss) || 0,
        }));
    };
    const handleContextMenu = (event, record) => {
        event.preventDefault();
        setCurrentRow(record);
        setContextMenuPosition({
            left: event.clientX,
            top: event.clientY,
        });
        setContextMenuVisible(true);
        
        // Add options to the context menu
        setContextMenuOptions([
            {
                label: "Visualizza Storico Ordini",
                key: "storico",
                onClick: () => handleStoricoOrdini(record.c_articolo, record.d_articolo)
            },
            {
                label: "Visualizza Dati Articolo",
                key: "articolo",
                onClick: () => handleAPClick(record.c_articolo)
            },
            // Add the new Kiosk option
            {
                label: "Visualizza Kiosk",
                key: "kiosk",
                onClick: () => handleKioskClick()
            }
        ]);
    };

    useEffect(() => {
        const errorHandler = (e) => {
            if (
                e.message.includes(
                    "ResizeObserver loop completed with undelivered notifications" ||
                    "ResizeObserver loop limit exceeded"
                )
            ) {
                const resizeObserverErr = document.getElementById(
                    "webpack-dev-server-client-overlay"
                );
                if (resizeObserverErr) {
                    resizeObserverErr.style.display = "none";
                }
            }
        };
        window.addEventListener("error", errorHandler);
        return () => {
            window.removeEventListener("error", errorHandler);
        };
    }, []);

    // Update fetchData to use environment variable
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/articles`);
                let fetchedData = parseIntegerData(response.data);

                // Sort the data based on 'c_articolo'
                fetchedData.sort((a, b) => a.c_articolo.localeCompare(b.c_articolo));

                setData(fetchedData);
                // Make sure hideZeroRows is set to true as default
                setHideZeroRows(true);
            } catch (error) {
                message.error("Failed to fetch data from the server.");
                console.error("Error fetching data:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []); // Remove API_BASE_URL from dependency array as it's imported and constant

    const handleStoricoOrdini = (articleCode, desc) => {
        // Open the modal and show loading spinner
        setIsOrderHistoryModalVisible(true);
        setOrderHistoryLoading(true);
        setOrderHistoryModalTitle(`Impegno corrente per articolo: ${articleCode} - ${desc}`);
        setOrderHistoryData([]); // Clear existing data

        // Fetch order history data
        fetchOrderHistoryData(articleCode);
    };

    const fetchOrderHistoryData = async (articleCode) => {
        try {
            // Fetch data from the backend
            const response = await axios.get(`${API_BASE_URL}/article_history`, {
                params: { article_code: articleCode },
            });

            const data = response.data;

            if (!Array.isArray(data) || data.length === 0) {
                message.info("No order history data available for this article.");
                setIsOrderHistoryModalVisible(false);
                setOrderHistoryLoading(false);
                return;
            }

            // Process data if necessary
            setOrderHistoryData(data);
        } catch (error) {
            message.error("Nessun impegno corrente trovato.");
            console.error("Error fetching order history data:", error);
            setIsOrderHistoryModalVisible(false);
        } finally {
            setOrderHistoryLoading(false);
        }
    };

    const relatedColumnsMap = {
        "disponibilita_m_corr": ["dom_mc", "off_mc"],
        "disponibilita_m_succ": ["dom_ms", "off_ms"],
        "disponibilita_2m_succ": ["dom_msa", "off_msa"],
        "disponibilita_3m_succ": ["dom_mss", "off_mss"],
    };

    const orderHistoryColumns = [
        {
            title: "Articolo",
            dataIndex: "mpf_arti",
            key: "mpf_arti",
        },
        {
            title: "Descrizione",
            dataIndex: "mpf_desc",
            key: "mpf_desc",
        },
        {
            title: "Data Cons.",
            dataIndex: "occ_dtco",
            key: "occ_dtco",
            render: (text) => text ? new Date(text).toLocaleDateString() : "",
        },

        {
            title: "T",
            dataIndex: "occ_tipo",
            key: "occ_tipo",
        },
        {
            title: "NrOrd",
            dataIndex: "occ_code",
            key: "occ_code",
        },
        {
            title: "Stato",
            dataIndex: "oct_stap",
            key: "oct_stap",
            render: (text) => {
                switch (text) {
                    case 'A':
                        return <Tag color="green">Aperto</Tag>;
                    case 'O':
                        return <Tag color="blue">Offerta</Tag>;
                    default:
                        return text;
                }
            },
        },


        {
            title: "Cliente",
            dataIndex: "oct_cocl",
            key: "oct_cocl",
        },
        {
            title: "Ragione Sociale",
            dataIndex: "des_clifor",
            key: "des_clifor",
        },
        {
            title: "Q.ta totale",
            dataIndex: "totale",
            key: "totale",
        },
        {
            title: "Residuo",
            dataIndex: "residuo",
            key: "residuo",
        },

    ];
    const contextMenu = (
        <Menu>
            {contextMenuOptions.map((option) => (
                <Menu.Item
                    key={option.key}
                    onClick={() => {
                        option.onClick();
                        setContextMenuVisible(false);
                    }}
                >
                    {option.label}
                </Menu.Item>
            ))}
        </Menu>
    );

    // Click handler for the "AP" column
    const handleAPClick = (articleCode) => {
        // Open the modal and show loading spinner
        setIsModalVisible(true);
        setChartLoading(true);
        setModalTitle(`Storico prezzi per aticolo: ${articleCode}`);
        setIsAverage(false); // Reset checkbox state
        setChartData([]); // Clear existing chart data
        setRawChartData([]);
        setAverageChartData([]);
        setMaxPriceData(null);
        setMinPriceData(null);
        setValuta(null);

        // Use setTimeout to delay the data fetching
        setTimeout(() => {
            fetchArticleData(articleCode);
        }, 0);
    };
    const fetchArticleData = async (articleCode) => {
        try {
            console.time('Total fetchArticleData time');

            console.time('API call time');
            // Fetch processed data from the backend
            const priceResponse = await axios.get(`${API_BASE_URL}/article_price`, {
                params: { article_code: articleCode },
            });
            console.timeEnd('API call time');

            console.time('Data processing time');
            const {
                rawData,
                averageData,
                valuta,
                maxPriceData,
                minPriceData,
            } = priceResponse.data;

            if (rawData.length === 0) {
                message.info("No price data available for this article.");
                setIsModalVisible(false);
                setChartLoading(false);
                console.timeEnd('Data processing time');
                console.timeEnd('Total fetchArticleData time');
                return;
            }

            console.log('Number of records in rawData:', rawData.length);
            console.log('Number of records in averageData:', averageData.length);

            // Measure time to set state
            console.time('setState time');
            setRawChartData(rawData);
            setAverageChartData(averageData);

            // Initially show raw data
            setChartData(rawData);

            // Set max and min price data
            setMaxPriceData(maxPriceData);
            setMinPriceData(minPriceData);

            setValuta(valuta);
            console.timeEnd('setState time');

            // Measure time to set chart loading
            console.time('setChartLoading time');
            setChartLoading(false);
            console.timeEnd('setChartLoading time');

            console.timeEnd('Data processing time');
            console.timeEnd('Total fetchArticleData time');

        } catch (error) {
            message.error("Impossibile trovare storico prezzi.");
            console.error("Error fetching article price data:", error);
            setIsModalVisible(false);
            setChartLoading(false);
            console.timeEnd('Data processing time');
            console.timeEnd('Total fetchArticleData time');
        }
    };

    const handleCheckboxChange = (e) => {
        const average = e.target.checked;
        setIsAverage(average);
        updateChartData(average);
    };

    const updateChartData = (average) => {
        if (average) {
            // In average mode, dates represent months
            setChartData(averageChartData);

            // Compute max and min values for average data
            const maxPriceData = averageChartData.reduce(
                (max, item) => (item.price > max.price ? item : max),
                averageChartData[0]
            );

            const minPriceData = averageChartData.reduce(
                (min, item) => (item.price < min.price ? item : min),
                averageChartData[0]
            );

            setMaxPriceData(maxPriceData);
            setMinPriceData(minPriceData);
        } else {
            // In raw mode, dates represent individual dates
            setChartData(rawChartData);

            // Compute max and min values for raw data
            const maxPriceData = rawChartData.reduce(
                (max, item) => (item.price > max.price ? item : max),
                rawChartData[0]
            );

            const minPriceData = rawChartData.reduce(
                (min, item) => (item.price < min.price ? item : min),
                rawChartData[0]
            );

            setMaxPriceData(maxPriceData);
            setMinPriceData(minPriceData);
        }
    };
    // Handle search text change for c_articolo
    const handleSearch = (selectedKeys, confirm) => {
        confirm();
        setSearchText(selectedKeys[0]);
    };

    const handleReset = (clearFilters) => {
        clearFilters();
        setSearchText("");
    };

    // Calculate current month's availability
    const calculateAvailability = (record, month) => {
        const giacD01 = record.giac_d01 || 0;

        if (month === "mc") {
            // First month (m corr.) starts from the D01 value
            return giacD01 - (record.dom_mc || 0) + (record.off_mc || 0);
        } else if (month === "ms") {
            // Next month (m succ.) starts from Disponibilità m corr.
            const currentMonthAvailability = calculateAvailability(record, "mc");
            return currentMonthAvailability - (record.dom_ms || 0) + (record.off_ms || 0);
        } else if (month === "msa") {
            // Following month (2m succ.) starts from Disponibilità m succ.
            const nextMonthAvailability = calculateAvailability(record, "ms");
            return nextMonthAvailability - (record.dom_msa || 0) + (record.off_msa || 0);
        } else if (month === "mss") {
            // Third successive month (3m+ succ.) starts from Disponibilità 2m succ.
            const secondMonthAvailability = calculateAvailability(record, "msa");
            return secondMonthAvailability - (record.dom_mss || 0) + (record.off_mss || 0);
        }
        return 0; // Default for undefined month parameter
    };


    const getAvailabilityCellClass = (value, scorta) => {
        if (value < 0) {
            return "cell-default cell-red";
        } else if (value < scorta) {
            return "cell-default cell-yellow";
        }
        return "cell-default";
    };
    // Define columns with filters
    const dataColumns = [
        {
            title: "Articolo", // Customized title
            dataIndex: "c_articolo",
            key: "c_articolo",
            render: (text) => <strong>{text}</strong>, // Makes each article text bold
            width: 100, // Fixed width

            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Input
                        placeholder="Cerca Articolo"
                        value={selectedKeys[0]}
                        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                        onPressEnter={() => handleSearch(selectedKeys, confirm)}
                        style={{ marginBottom: 8, display: "block" }}
                    />
                    <Button
                        type="primary"
                        onClick={() => handleSearch(selectedKeys, confirm)}
                        icon={<SearchOutlined />}
                        size="small"
                        style={{ width: 90, marginRight: 8 }}
                    >
                        Cerca
                    </Button>
                    <Button onClick={() => handleReset(clearFilters)} size="small" style={{ width: 90 }}>
                        Reset
                    </Button>
                </div>
            ),
            filterIcon: (filtered) => (
                <SearchOutlined
                  style={{
                    color: filtered ? '#1677ff' : undefined,
                  }}
                />
              ),
            onFilter: (value, record) =>
                record.c_articolo.toString().toLowerCase().includes(value.toLowerCase()),
        },
        {
            title: "AP", // Customized title for 'a_p'
            dataIndex: "a_p",
            key: "a_p",
            width: 50,
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Checkbox.Group
                        options={[
                            { label: "A", value: "A" },
                            { label: "P", value: "P" },
                        ]}
                        value={selectedKeys}
                        onChange={(checkedValues) => setSelectedKeys(checkedValues)}
                    />
                    <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            size="small"
                            style={{ width: 90, marginRight: 8 }}
                        >
                            Applica
                        </Button>
                        <Button onClick={() => handleReset(clearFilters)} size="small" style={{ width: 90 }}>
                            Reset
                        </Button>
                    </div>
                </div>
            ),
            onFilter: (value, record) => {
                if (Array.isArray(value)) {
                    return value.includes(record.a_p);
                }
                return record.a_p === value;
            },
            defaultFilteredValue: ["A"],
        },
        // Add additional columns with customized titles
        {
            title: 'Descrizione',
            dataIndex: 'd_articolo',
            key: 'd_articolo',
            width: 200, // Optional: set a fixed width for consistency
            render: (text) => {
                let truncatedText = text;
                if (text.length > 45) {
                    truncatedText = text.slice(0, 45);
                }
                return (
                    <AntTooltip title={text}>
                        {truncatedText}
                    </AntTooltip>
                );
            },
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Input
                        placeholder="Cerca Descrizione"
                        value={selectedKeys[0]}
                        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
                        onPressEnter={() => handleSearch(selectedKeys, confirm)}
                        style={{ marginBottom: 8, display: "block" }}
                    />
                    <Button
                        type="primary"
                        onClick={() => handleSearch(selectedKeys, confirm)}
                        icon={<SearchOutlined />}
                        size="small"
                        style={{ width: 90, marginRight: 8 }}
                    >
                        Cerca
                    </Button>
                    <Button onClick={() => handleReset(clearFilters)} size="small" style={{ width: 90 }}>
                        Reset
                    </Button>
                </div>
            ),
            filterIcon: (filtered) => (
                <SearchOutlined
                  style={{
                    color: filtered ? '#1677ff' : undefined,
                  }}
                />
              ),
            onFilter: (value, record) =>
                record.d_articolo.toString().toLowerCase().includes(value.toLowerCase()),
        },
        {
            title: "LT", // Customize for another field
            dataIndex: "lt",
            key: "lt",
        },
        {
            title: "SCRT", // Customize for another field
            dataIndex: "scrt",
            key: "scrt",
        },
        {
            title: "Dep. 1", // Customize for another field
            dataIndex: "giac_d01",
            key: "giac_d01",
        },
        //{
        //    title: "Dep. 20", // Customize for another field
        //    dataIndex: "giac_d20",
    //    key: "giac_d20",
      //},
        {
            title: "Dep. 32", // Customize for another field
            dataIndex: "giac_d32",
            key: "giac_d32",
        },
        {
            title: "Dep. 40", // Customize for another field
            dataIndex: "giac_d40",
            key: "giac_d40",
        },
        {
            title: "Dep. 48", // Customize for another field
            dataIndex: "giac_d48",
            key: "giac_d48",
        },
        {
            title: "Dep. 60", // Customize for another field
            dataIndex: "giac_d60",
            key: "giac_d60",
        },
        {
            title: "Dep. 81", // Customize for another field
            dataIndex: "giac_d81",
            key: "giac_d81",
        },
        {
            title: "Disp. m corr.",
            dataIndex: "disponibilita_m_corr",
            key: "disponibilita_m_corr",
            width: "max-content", // Set column width

            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Radio.Group
                        onChange={(e) => {
                            const value = e.target.value;
                            if (value === "all") {
                                clearFilters();
                            } else {
                                setSelectedKeys([value]);
                            }
                        }}
                        value={selectedKeys[0] || "all"}
                        style={{ width: "100%" }}
                    >
                        <Radio.Button value="all">Tutti</Radio.Button>
                        <Radio.Button value="negative">Solo Negativi</Radio.Button>
                        <Radio.Button value="underScorta">Solo Sotto Scorta</Radio.Button>
                    </Radio.Group>
                    <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            size="small"
                            style={{ width: 90, marginRight: 8 }}
                        >
                            Applica
                        </Button>
                        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 90 }}>
                            Reset
                        </Button>
                    </div>
                </div>
            ),
            onFilter: (value, record) => {
                const availability = calculateAvailability(record, "mc");
                if (value === "negative") {
                    return availability < 0;
                }
                if (value === "underScorta") {
                    return availability < record.scrt;
                }
                return true; // For "all", include all rows
            },
            render: (_, record) => {
                const value = calculateAvailability(record, "mc");
                const cellClass = getAvailabilityCellClass(value, record.scrt);

                const handleMouseEnter = () => {
                    if (true) {
                        setHoveredRowKey(record.c_articolo);
                        setHighlightedColumns(relatedColumnsMap["disponibilita_m_corr"]);
                    }
                };

                const handleMouseLeave = () => {
                    setHoveredRowKey(null);
                    setHighlightedColumns([]);
                };

                return (
                    <div
                        className={cellClass}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                    >
                        {value}
                    </div>
                );
            },
        },
        {
            title: "Disp. m succ.",
            dataIndex: "disponibilita_m_succ",
            key: "disponibilita_m_succ",
            width: "max-content", // Set column width

            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Radio.Group
                        onChange={(e) => {
                            const value = e.target.value;
                            if (value === "all") {
                                clearFilters();
                            } else {
                                setSelectedKeys([value]);
                            }
                        }}
                        value={selectedKeys[0] || "all"}
                        style={{ width: "100%" }}
                    >
                        <Radio.Button value="all">Tutti</Radio.Button>
                        <Radio.Button value="negative">Solo Negativi</Radio.Button>
                        <Radio.Button value="underScorta">Solo Sotto Scorta</Radio.Button>
                    </Radio.Group>
                    <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            size="small"
                            style={{ width: 90, marginRight: 8 }}
                        >
                            Applica
                        </Button>
                        <Button
                            onClick={() => {
                                clearFilters();
                                confirm();
                            }}
                            size="small"
                            style={{ width: 90 }}
                        >
                            Reset
                        </Button>
                    </div>
                </div>
            ),
            onFilter: (value, record) => {
                const availability = calculateAvailability(record, "ms");
                if (value === "negative") {
                    return availability < 0;
                }
                if (value === "underScorta") {
                    return availability < record.scrt;
                }
                return true; // For "all", include all rows
            },
            render: (_, record) => {
                const value = calculateAvailability(record, "ms");
                const cellClass = getAvailabilityCellClass(value, record.scrt);

                const handleMouseEnter = () => {
                    if (true) {
                        setHoveredRowKey(record.c_articolo);
                        setHighlightedColumns(relatedColumnsMap["disponibilita_m_succ"]);
                    }
                };

                const handleMouseLeave = () => {
                    setHoveredRowKey(null);
                    setHighlightedColumns([]);
                };

                return (
                    <div
                        className={cellClass}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                    >
                        {value}
                    </div>
                );
            },
        },
        // Disp. 2m succ.
        {
            title: "Disp. 2m succ.",
            dataIndex: "disponibilita_2m_succ",
            key: "disponibilita_2m_succ",
            width: "max-content", // Set column width

            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Radio.Group
                        onChange={(e) => {
                            const value = e.target.value;
                            if (value === "all") {
                                clearFilters();
                            } else {
                                setSelectedKeys([value]);
                            }
                        }}
                        value={selectedKeys[0] || "all"}
                        style={{ width: "100%" }}
                    >
                        <Radio.Button value="all">Tutti</Radio.Button>
                        <Radio.Button value="negative">Solo Negativi</Radio.Button>
                        <Radio.Button value="underScorta">Solo Sotto Scorta</Radio.Button>
                    </Radio.Group>
                    <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            size="small"
                            style={{ width: 90, marginRight: 8 }}
                        >
                            Applica
                        </Button>
                        <Button
                            onClick={() => {
                                clearFilters();
                                confirm();
                            }}
                            size="small"
                            style={{ width: 90 }}
                        >
                            Reset
                        </Button>
                    </div>
                </div>
            ),
            onFilter: (value, record) => {
                const availability = calculateAvailability(record, "msa");
                if (value === "negative") {
                    return availability < 0;
                }
                if (value === "underScorta") {
                    return availability < record.scrt;
                }
                return true; // For "all", include all rows
            },
            render: (_, record) => {
                const value = calculateAvailability(record, "msa");
                const cellClass = getAvailabilityCellClass(value, record.scrt);

                const handleMouseEnter = () => {
                    if (true) {
                        setHoveredRowKey(record.c_articolo);
                        setHighlightedColumns(relatedColumnsMap["disponibilita_2m_succ"]);
                    }
                };

                const handleMouseLeave = () => {
                    setHoveredRowKey(null);
                    setHighlightedColumns([]);
                };

                return (
                    <div
                        className={cellClass}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                    >
                        {value}
                    </div>
                );
            },
        },
        // Disp. 3m+ succ.
        {
            title: "Disp. 3m+ succ.",
            dataIndex: "disponibilita_3m_succ",
            key: "disponibilita_3m_succ",
            width: "max-content", // Adjust as needed

            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <Radio.Group
                        onChange={(e) => {
                            const value = e.target.value;
                            if (value === "all") {
                                clearFilters();
                            } else {
                                setSelectedKeys([value]);
                            }
                        }}
                        value={selectedKeys[0] || "all"}
                        style={{ width: "100%" }}
                    >
                        <Radio.Button value="all">Tutti</Radio.Button>
                        <Radio.Button value="negative">Solo Negativi</Radio.Button>
                        <Radio.Button value="underScorta">Solo Sotto Scorta</Radio.Button>
                    </Radio.Group>
                    <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
                        <Button
                            type="primary"
                            onClick={() => confirm()}
                            size="small"
                            style={{ width: 90, marginRight: 8 }}
                        >
                            Applica
                        </Button>
                        <Button
                            onClick={() => {
                                clearFilters();
                                confirm();
                            }}
                            size="small"
                            style={{ width: 90 }}
                        >
                            Reset
                        </Button>
                    </div>
                </div>
            ),
            onFilter: (value, record) => {
                const availability = calculateAvailability(record, "mss");
                if (value === "negative") {
                    return availability < 0;
                }
                if (value === "underScorta") {
                    return availability < record.scrt;
                }
                return true; // For "all", include all rows
            },
            render: (_, record) => {
                const value = calculateAvailability(record, "mss");
                const cellClass = getAvailabilityCellClass(value, record.scrt);

                const handleMouseEnter = () => {
                    if (true) {
                        setHoveredRowKey(record.c_articolo);
                        setHighlightedColumns(relatedColumnsMap["disponibilita_3m_succ"]);
                    }
                };

                const handleMouseLeave = () => {
                    setHoveredRowKey(null);
                    setHighlightedColumns([]);
                };

                return (
                    <div
                        className={cellClass}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={handleMouseLeave}
                    >
                        {value}
                    </div>
                );
            },
        },
        {
            title: "Ordine 2m prec.", // Customize for another field
            dataIndex: "ord_mpp",
            key: "ord_mpp",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("ord_mpp");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {text}
                    </div>
                );
            },
        },
        {
            title: "Ordine m prec.", // Customize for another field
            dataIndex: "ord_mp",
            key: "ord_mp",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("ord_mp");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {text}
                    </div>
                );
            },
        },
        {
            title: "Ordine m corr.", // Customize for another field
            dataIndex: "ord_mc",
            key: "ord_mc",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("ord_mc");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {text}
                    </div>
                );
            },
        },
        {
            title: "Impegno m corr.", // Customize for another field
            dataIndex: "dom_mc",
            key: "dom_mc",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("dom_mc");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Impegno m corr.">
                                {text}
                            </AntTooltip> :
                            text
                        }
                    </div>
                );
            },
        },
        {
            title: "Impegno m succ.", // Customize for another field
            dataIndex: "dom_ms",
            key: "dom_ms",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("dom_ms");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Impegno m succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }

                    </div>
                );
            },
        },
        {
            title: "Impegno 2m succ.", // Customize for another field
            dataIndex: "dom_msa",
            key: "dom_msa",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("dom_msa");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Impegno 2m succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }                    </div>
                );
            },
        },
        {
            title: "Impegno 3m+ succ.", // Customize for another field
            dataIndex: "dom_mss",
            key: "dom_mss",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("dom_mss");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Impegno 3m+ succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }                    </div>
                );
            },
        },
        {
            title: "Atteso m corr.", // Customize for another field
            dataIndex: "off_mc",
            key: "off_mc",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("off_mc");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Atteso m corr.">
                                {text}
                            </AntTooltip> :
                            text
                        }                    </div>
                );
            },
        },
        {
            title: "Atteso m succ.", // Customize for another field
            dataIndex: "off_ms",
            key: "off_ms",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("off_ms");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Atteso m succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }
                    </div>
                );
            },
        },
        {
            title: "Atteso 2m succ.", // Customize for another field
            dataIndex: "off_msa",
            key: "off_msa",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("off_msa");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Atteso 2m succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }
                    </div>
                );
            },
        },
        {
            title: "Atteso 3m+ succ.", // Customize for another field
            dataIndex: "off_mss",
            key: "off_mss",
            render: (text, record) => {
                const shouldHighlight = (hoveredRowKey === record.c_articolo) && highlightedColumns.includes("off_mss");
                return (
                    <div className={shouldHighlight ? "highlighted-cell" : ""}>
                        {shouldHighlight ?
                            <AntTooltip defaultOpen={true} title="Atteso 3m+ succ.">
                                {text}
                            </AntTooltip> :
                            text
                        }
                    </div>
                );
            },
        },
    ];
    const columnsToCheck = [
        "ord_mpp", "ord_mp", "ord_mc",
        "dom_mc", "dom_ms", "dom_msa", "dom_mss",
        "off_mc", "off_ms", "off_msa", "off_mss",
        "giac_d01", "giac_d20", "giac_d32", "giac_d40", "giac_d48", "giac_d60", "giac_d81"
    ];

    const filteredData = hideZeroRows
        ? data.filter(item => {
            // Check if there's at least one non-zero value in the columns we're checking
            return columnsToCheck.some(key => item[key] !== 0);
        })
        : data;
    const [visibleDataColumns, setVisibleDataColumns] = useState(dataColumns.map(col => col.key));
    const [isColumnSelectorVisible, setIsColumnSelectorVisible] = useState(false);
    const handleClickOutside = () => {
        if (contextMenuVisible) {
            setContextMenuVisible(false);
        }
    };
    useEffect(() => {
        document.addEventListener("click", handleClickOutside);
        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    }, [contextMenuVisible]);

    const exportExcel = () => {
        // Define the columns to include in the export
        const exportData = data.map((item) => ({
            "Articolo": item.c_articolo,
            "AP": item.a_p,
            "Descrizione": item.d_articolo,
            "LT": item.lt,
            "SCRT": item.scrt,
            "Dep. 1": item.giac_d01,
            "Dep. 20": item.giac_d20,
            "Dep. 32": item.giac_d32,
            "Dep. 40": item.giac_d40,
            "Dep. 48": item.giac_d48,
            "Dep. 60": item.giac_d60,
            "Dep. 81": item.giac_d81,
            "Disponibilità m corr.": calculateAvailability(item, "mc"),
            "Disponibilità m succ.": calculateAvailability(item, "ms"),
            "Disponibilità 2m succ.": calculateAvailability(item, "msa"),
            "Disponibilità 3m+ succ.": calculateAvailability(item, "mss"),

            "Ordine 2m prec.": item.ord_mpp,
            "Ordine m prec.": item.ord_mp,
            "Ordine m corr.": item.ord_mc,
            "Impegno m corr.": item.dom_mc,
            "Impegno m succ.": item.dom_ms,
            "Impegno 2m succ.": item.dom_msa,
            "Impegno 3m+ succ.": item.dom_mss,
            "Atteso m corr.": item.off_mc,
            "Atteso m succ.": item.off_ms,
            "Atteso 2m succ.": item.off_msa,
            "Atteso 3m+ succ.": item.off_mss,
        }));

        // Create a worksheet from the data
        const worksheet = XLSX.utils.json_to_sheet(exportData);

        // Create a new workbook and append the worksheet
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Articoli");

        // Generate a buffer
        const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });

        // Create a Blob from the buffer
        const dataBlob = new Blob([excelBuffer], { type: "application/octet-stream" });

        // Trigger the download using FileSaver
        saveAs(dataBlob, "Articoli.xlsx");
    };

    const todayOrdersColumns = [
        {
            title: "Data",
            dataIndex: "oct_data",
            key: "oct_data",
            render: (text) => text ? new Date(text).toLocaleDateString() : "",
        },
        {
            title: "Tipo",
            dataIndex: "oct_tipo",
            key: "oct_tipo",
        },
        {
            title: "NrOrd",
            dataIndex: "oct_code",
            key: "oct_code",
        },
        {
            title: "Cliente",
            dataIndex: "oct_cocl",
            key: "oct_cocl",
        },
        {
            title: "Ragione Sociale",
            dataIndex: "des_clifor",
            key: "des_clifor",
        },
        {
            title: "Riga",
            dataIndex: "occ_riga",
            key: "occ_riga",
        },
        {
            title: "Articolo",
            dataIndex: "occ_arti",
            key: "occ_arti",
        },
        {
            title: "Descrizione",
            dataIndex: "descrizione",
            key: "descrizione",
        },
        {
            title: "Quantità",
            dataIndex: "qty",
            key: "qty",
        },
        {
            title: "Data Consegna",
            dataIndex: "occ_dtco",
            key: "occ_dtco",
            render: (text) => text ? new Date(text).toLocaleDateString() : "",
        },
        {
            title: "Stock",
            dataIndex: "stock",
            key: "stock",
        },
        {
            title: "Arrivo Mese",
            dataIndex: "arrmonth",
            key: "arrmonth",
        },
        {
            title: "Arrivo Mese Successivo",
            dataIndex: "arrnextmonth",
            key: "arrnextmonth",
        },
        {
            title: "Arrivo Mese Seguente",
            dataIndex: "arrfollowing",
            key: "arrfollowing",
        },
    ];


    const fetchTodayOrdersData = async () => {
        try {
            const todayOrdersResponse = await axios.get(`${API_BASE_URL}/today_orders`);
            const todayOrdersData = todayOrdersResponse.data;

            if (!Array.isArray(todayOrdersData) || todayOrdersData.length === 0) {
                message.info("Nessun ordine inserito oggi.");
                setIsTodayOrdersModalVisible(false);
                setTodayOrdersLoading(false);
                return;
            }

            setTodayOrdersData(todayOrdersData);
        } catch (error) {
            message.error("Impossibile recuperare gli ordini odierni.");
            console.error("Error fetching today's orders data:", error);
            setIsTodayOrdersModalVisible(false);
        } finally {
            setTodayOrdersLoading(false);
        }
    };

    const handleTodayOrdersClick = () => {
        setIsTodayOrdersModalVisible(true);
        setTodayOrdersLoading(true);
        setTodayOrdersModalTitle("Ordini Odierni");

        // Fetch Today's Orders Data
        fetchTodayOrdersData();
    };
    const nascondiRighe = () => {
        setHideZeroRows(!hideZeroRows)
        message.info("Righe aggiornate")
    };

    // Add this function to handle adding a new row
    const handleAddSimulationRow = () => {
        setSimulationRows([...simulationRows, { code: '', quantity: '' }]);
    };

    // Add this function to handle updating a row
    const handleSimulationRowChange = (index, field, value) => {
        const updatedRows = [...simulationRows];
        updatedRows[index][field] = value;
        setSimulationRows(updatedRows);
    };

    // Add this function to handle removing a row
    const handleRemoveSimulationRow = (index) => {
        if (simulationRows.length > 1) {
            const updatedRows = simulationRows.filter((_, i) => i !== index);
            setSimulationRows(updatedRows);
        }
    };

    // Update the handleSimulate function to call an API
    const handleSimulate = async () => {
        // Validate that at least one row has both code and quantity
        const hasValidData = simulationRows.some(row => row.code.trim() !== '' && row.quantity.trim() !== '');
        
        if (!hasValidData) {
            message.error('Inserire almeno un codice articolo e una quantità valida');
            return;
        }
        
        // Filter out empty rows
        const validRows = simulationRows.filter(row => row.code.trim() !== '' && row.quantity.trim() !== '');
        
        setSimulationLoading(true);
        setSimulationComplete(false);
        
        try {
            // Call the API endpoint with time period
            const response = await axios.post(`${API_BASE_URL}/simulate_order`, {
                items: validRows,
                time_period: selectedTimePeriod
            });
            
            // Store the results
            setSimulationResults(response.data);
            setSimulationComplete(true);
            message.success('Simulazione completata con successo');
        } catch (error) {
            console.error('Error during simulation:', error);
            message.error('Errore durante la simulazione. Riprova più tardi.');
        } finally {
            setSimulationLoading(false);
        }
    };

    // Add this to reset the simulation modal state completely
    const handleCloseSimulationModal = () => {
        setIsSimulationModalVisible(false);
        setSimulationRows([{ code: '', quantity: '' }]);
        setSimulationResults([]);
        setSimulationComplete(false);
        setSelectedTimePeriod('today'); // Reset the time period as well
    };

    // Define columns for simulation results table
    const simulationResultsColumns = [
        {
            title: "Codice",
            dataIndex: "code",
            key: "code",
        },
        {
            title: "Descrizione",
            dataIndex: "description",
            key: "description",
        },
        {
            title: "Codici Padre",
            dataIndex: "parent_codes",
            key: "parent_codes",
        },
        {
            title: "Quantità Richiesta",
            dataIndex: "requested_quantity",
            key: "requested_quantity",
        },
        {
            title: "Disponibilità Attuale",
            dataIndex: "current_availability",
            key: "current_availability",
            render: (value) => {
                if (value < 0) {
                    return <span style={{ color: 'red' }}>{value}</span>;
                }
                return value;
            },
        },
        {
            title: "Disponibilità dopo Simulazione",
            dataIndex: "simulated_availability",
            key: "simulated_availability",
            render: (value) => {
                if (value < 0) {
                    return <span style={{ color: 'red' }}>{value}</span>;
                }
                return value;
            },
        },
        {
            title: "Stato",
            dataIndex: "status",
            key: "status",
            render: (text) => {
                switch (text) {
                    case 'OK':
                        return <Tag color="green">Disponibile</Tag>;
                    case 'PARTIAL':
                        return <Tag color="orange">Parzialmente Disponibile</Tag>;
                    case 'NOT_AVAILABLE':
                        return <Tag color="red">Non Disponibile</Tag>;
                    default:
                        return text;
                }
            },
        },
    ];

    // Update handleKioskClick to properly find articles in the main data using case-insensitive matching
    const handleKioskClick = () => {
        // Predefined list of article codes for Kiosk
        const kioskArticleCodes = [
            '0AC618MC', '0AC619MC', '0AC620MC', '0AC621MC', '0AC641MC',
            '0AC642MC', '0AC625MC', '0AC637MC', '69120005', 'GUIDEKIOSK32',
            '0AC423501', '53082108', '69120006', '69120009', '66319015',
            '69120016', '61820003', '61820005', '66319008', '69120007',
            '61920001', '69120018', '61820004', '58742030', '58742031',
            '0AC100WE', '0AC961FI', '0AC640MC', '0AC623MC'
        ];
        
        // Reset filter when opening the modal
        setKioskFilter('');

        // Display a loading message
        message.loading({ content: 'Caricamento dati Kiosk...', key: 'kioskLoading' });
        
        console.log(`Searching for Kiosk articles among ${data.length} total articles`);
        
        // Get all articles that match any of the Kiosk codes (case-insensitive)
        const matchedArticles = data.filter(item => 
            kioskArticleCodes.some(code => 
                code.toLowerCase() === item.c_articolo.toLowerCase().trim()
            )
        );
        
        console.log(`Found ${matchedArticles.length} matching Kiosk articles in real data`);
        
        // Create a map of actual articles by code (lowercase for case-insensitive matching)
        const articlesMap = new Map();
        data.forEach(item => {
            articlesMap.set(item.c_articolo.toLowerCase().trim(), item);
        });
        
        // Start with matched articles
        let finalKioskData = [...matchedArticles];
        
        // Check for missing codes and create placeholders with "NOT FOUND" description 
        // but maintain proper structure from a real article
        const matchedCodes = matchedArticles.map(item => item.c_articolo.toLowerCase().trim());
        const missingCodes = kioskArticleCodes.filter(code => 
            !matchedCodes.includes(code.toLowerCase().trim())
        );
        
        console.log(`Missing ${missingCodes.length} Kiosk articles in data`);
        
        // If we have missing codes, create proper placeholders based on a real article's structure
        if (missingCodes.length > 0 && data.length > 0) {
            // Use an existing article as template for structure
            const templateArticle = data[0];
            
            // Create placeholders for missing codes
            const placeholderArticles = missingCodes.map(code => {
                // Create a placeholder based on the template, with all zeros for numeric fields
                const placeholder = { ...templateArticle };
                
                // Reset all numeric fields to 0
                Object.keys(placeholder).forEach(key => {
                    if (typeof placeholder[key] === 'number') {
                        placeholder[key] = 0;
                    }
                });
                
                // Set the article code and description fields
                placeholder.c_articolo = code;
                placeholder.d_articolo = `Articolo Kiosk ${code} - NON TROVATO`;
                placeholder.a_p = 'A';
                placeholder.isPlaceholder = true;
                
                return placeholder;
            });
            
            // Add placeholders to final data set
            finalKioskData = [...finalKioskData, ...placeholderArticles];
        }
        
        // Sort by article code
        finalKioskData.sort((a, b) => a.c_articolo.localeCompare(b.c_articolo));
        
        // Open modal and set data
        setIsKioskModalVisible(true);
        setKioskData(finalKioskData);
        
        // Show appropriate message
        if (matchedArticles.length === 0) {
            message.info({ 
                content: `Non sono stati trovati articoli Kiosk nel database (${missingCodes.length} mancanti)`, 
                key: 'kioskLoading',
                duration: 5
            });
        } else if (missingCodes.length > 0) {
            message.success({ 
                content: `Trovati ${matchedArticles.length} articoli reali. ${missingCodes.length} articoli non trovati nel database`, 
                key: 'kioskLoading',
                duration: 5
            });
        } else {
            message.success({ 
                content: `Trovati tutti i ${matchedArticles.length} articoli Kiosk nel database`, 
                key: 'kioskLoading' 
            });
        }
    };
    
    // Add back the handleUpdateKioskData function
    const handleUpdateKioskData = () => {
        handleKioskClick();
    };
    
    // Add back the kioskSelectionOptions
    const kioskSelectionOptions = [
        { value: 'Kiosk', label: 'Kiosk Standard' },
        { value: 'KioskSelf', label: 'Kiosk Self-Service' },
        { value: 'KioskXPos', label: 'Kiosk XPos' }
    ];

    // Now the menu2 definition can reference handleKioskClick properly
    const menu2 = (
        <Menu>
            <Menu.Item key="todayOrders" onClick={handleTodayOrdersClick}>
                Ordini Odierni
            </Menu.Item>
            <Menu.Item key="simulateOrder" onClick={() => setIsSimulationModalVisible(true)}>
                Simula Ordine
            </Menu.Item>
            <Menu.Item key="showKiosk" onClick={handleKioskClick}>
                Visualizza Kiosk
            </Menu.Item>
            <Menu.Item key="exportExcel" onClick={exportExcel}>
                Export Excel
            </Menu.Item>
            <Menu.Item key="columnSelector" onClick={() => setIsColumnSelectorVisible(true)}>
                Seleziona Colonne
            </Menu.Item>
        </Menu>
    );

    const columns = [
        {
            title: (
                <Dropdown overlay={menu2} trigger={["click"]}>
                    <Button icon={<MenuFoldOutlined />} />
                </Dropdown>
            ),
            key: "action",
            width: 50,
            fixed: "left",
            render: (text, record) => {
                const menu = (
                    <Menu>
                        <Menu.Item
                            key="displayModal"
                            onClick={() => handleAPClick(record.c_articolo)}
                        >
                            Storico Prezzi
                        </Menu.Item>
                        <Menu.Item
                            key="storicoOrdini"
                            onClick={() => handleStoricoOrdini(record.c_articolo, record.d_articolo)}
                        >
                            Impegno corrente
                        </Menu.Item>
                    </Menu>
                );

                return (
                    <Dropdown overlay={menu} trigger={["click"]}>
                        <Button icon={<EllipsisOutlined />} />
                    </Dropdown>
                );
            },
        },
        ...dataColumns.filter(col => visibleDataColumns.includes(col.key)),
    ];


    // Custom Legend Component
    const CustomLegend = () => {
        return (
            <div style={{ textAlign: "left", marginLeft: 10 }}>
                <div>
                    <strong>Valuta:</strong> {valuta}
                </div>
                <div>
                    <strong>Max:</strong> {maxPriceData.price.toFixed(2)} - {new Date(maxPriceData.date).toLocaleDateString()}
                </div>
                <div>
                    <strong>Min:</strong> {minPriceData.price.toFixed(2)} - {new Date(minPriceData.date).toLocaleDateString()}
                </div>

                <Checkbox
                    checked={isAverage}
                    onChange={handleCheckboxChange}
                    style={{ marginBottom: 10 }}
                >
                    Media per mese
                </Checkbox>
            </div>
        );
    };
    
    // Update the Kiosk modal render function to better handle placeholders and use the same styling as main table
    const renderKioskModal = () => {
        // Filter the kioskData based on user input if there's a filter value
        const filteredKioskData = kioskFilter 
            ? kioskData.filter(item => 
                item.c_articolo.toLowerCase().includes(kioskFilter.toLowerCase()) ||
                item.d_articolo.toLowerCase().includes(kioskFilter.toLowerCase())
              )
            : kioskData;
            
        // Count real articles vs placeholders
        const placeholderCount = kioskData.filter(item => item.isPlaceholder).length;
        const realCount = kioskData.length - placeholderCount;

        // Create columns with modified render functions to highlight placeholders
        const kioskColumns = columns.map(col => {
            // Special rendering for c_articolo and d_articolo columns to highlight placeholders
            if (col.dataIndex === 'c_articolo' || col.dataIndex === 'd_articolo') {
                return {
                    ...col,
                    render: (text, record) => {
                        if (record.isPlaceholder) {
                            return (
                                <span style={{ color: '#ff4d4f', fontStyle: 'italic' }}>
                                    {text} {col.dataIndex === 'c_articolo' && 
                                    <Tag color="error" style={{ marginLeft: 4 }}>Non trovato</Tag>}
                                </span>
                            );
                        }
                        return col.render ? col.render(text, record) : text;
                    }
                };
            }
            // For numeric fields in placeholders, show dash instead of zero
            if (['giac_d01', 'giac_d20', 'giac_d32', 'giac_d40', 'giac_d48', 
                 'giac_d60', 'giac_d81', 'dom_mc', 'dom_ms', 'dom_msa', 'dom_mss',
                 'off_mc', 'off_ms', 'off_msa', 'off_mss'].includes(col.dataIndex)) {
                return {
                    ...col,
                    render: (text, record) => {
                        if (record.isPlaceholder) {
                            return <span style={{ color: '#8c8c8c' }}>-</span>;
                        }
                        return col.render ? col.render(text, record) : text;
                    }
                };
            }
            return col;
        });

        return (
            <Modal
                title={`Dettaglio Articoli ${selectedKiosk}`}
                visible={isKioskModalVisible}
                onCancel={() => {
                    setIsKioskModalVisible(false);
                    setKioskFilter('');
                }}
                footer={null}
                width="100%"
                style={{ top: 0 }}
                bodyStyle={{ height: 'calc(100vh - 57px)', overflow: 'auto' }}
            >
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                        <Select
                            value={selectedKiosk}
                            onChange={value => setSelectedKiosk(value)}
                            style={{ width: 200, marginRight: 8 }}
                            options={kioskSelectionOptions}
                        />
                        <Button type="primary" onClick={handleUpdateKioskData} style={{ marginRight: 8 }}>Aggiorna</Button>
                        <Button onClick={() => setKioskFilter('')} disabled={!kioskFilter}>
                            Reset Filtri
                        </Button>
                    </div>
                    <div>
                        <Input.Search
                            placeholder="Filtra per codice o descrizione"
                            value={kioskFilter}
                            onChange={e => setKioskFilter(e.target.value)}
                            style={{ width: 300 }}
                            allowClear
                        />
                    </div>
                </div>
                
                {kioskData.length === 0 ? (
                    <Alert
                        message="Nessun articolo Kiosk trovato"
                        description="Verifica che i codici articolo Kiosk siano presenti nei dati caricati nella tabella principale."
                        type="warning"
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                ) : (
                    <Alert 
                        message={
                            <div>
                                <span>Mostrati {filteredKioskData.length} articoli</span>
                                {placeholderCount > 0 && (
                                    <span style={{ marginLeft: 8 }}>
                                        ({realCount > 0 ? `${realCount} trovati, ` : ''}{placeholderCount} non trovati)
                                    </span>
                                )}
                                {kioskFilter && <span style={{ marginLeft: 8 }}>(filtrati)</span>}
                            </div>
                        }
                        description={
                            placeholderCount > 0 && 
                            "Gli articoli in rosso sono codici non trovati nel database. Verificare i codici o aggiornare la lista predefinita."
                        }
                        type={placeholderCount > 0 ? "warning" : "info"} 
                        showIcon 
                        style={{ marginBottom: 16 }}
                    />
                )}
                
                <div className="table-container" style={{ height: 'calc(90vh - 170px)' }}>
                    <Table
                        bordered
                        columns={kioskColumns}
                        dataSource={filteredKioskData}
                        rowKey="c_articolo"
                        scroll={{ x: 1600, y: 650 }}
                        size="small"
                        pagination={false}
                        virtual
                        locale={{ emptyText: 'Nessun dato disponibile' }}
                        rowClassName={record => record.isPlaceholder ? 'placeholder-row' : ''}
                    />
                </div>
            </Modal>
        );
    };

    return (
        <>

            <div className="table-container">
                <Spin
                    indicator={<LoadingOutlined spin />}
                    size="large"
                    spinning={loading}
                    tip="Carico i dati..."
                >
                    <Table
                        bordered
                        dataSource={filteredData}
                        columns={columns}
                        rowKey="c_articolo"
                        pagination={false}
                        scroll={{
                            x: 1600,
                            y: 750, // Adjust based on your layout needs
                        }}
                        virtual
                        onRow={(record, rowIndex) => {
                            return {
                                onContextMenu: (event) => handleContextMenu(event, record), // Attach context menu handler
                            };
                        }}
                    />
                </Spin>

                {/* Render the context menu */}
                {contextMenuVisible && (
                    <div
                        style={{
                            position: "fixed",
                            top: contextMenuPosition.top,
                            left: contextMenuPosition.left,
                            zIndex: 1000,
                            background: "#fff",
                            boxShadow: "0px 0px 6px rgba(0,0,0,0.2)",
                            borderRadius: "4px",
                        }}
                        onContextMenu={(e) => e.preventDefault()} // Prevent default context menu on the custom menu
                    >
                        {contextMenu}
                    </div>
                )}

                {/* Modal for displaying the line chart */}
                <Modal
                    title={modalTitle}
                    visible={isModalVisible}
                    onCancel={() => setIsModalVisible(false)}
                    afterClose={() => {
                        // Reset state variables after the modal has closed
                        setChartData([]);
                        setMaxPriceData(null);
                        setMinPriceData(null);
                        setRawChartData([]);
                        setAverageChartData([]);
                        setIsAverage(false);
                        setValuta(null);
                    }}
                    footer={null}
                    width={900}
                >
                    {chartLoading ? (
                        <div style={{ textAlign: "center", padding: "50px 0" }}>
                              <Spin
                    indicator={<LoadingOutlined spin />}
                    size="large" tip="Caricamento storico prezzi..." />
                        </div>
                    ) : (
                        <div>
                            <div style={{ display: "flex", justifyContent: "center" }}>
                                <LineChart
                                    width={800}
                                    height={500}
                                    data={chartData}
                                    margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis
                                        dataKey="date"
                                        angle={-45}
                                        textAnchor="end"
                                        tickFormatter={(dateValue) => {
                                            if (isAverage) {
                                                // In average mode, dateValue represents a month string like '2023-10'
                                                const date = new Date(dateValue + '-01'); // Append '-01' to create a valid date
                                                return date.toLocaleString('default', { month: 'short', year: 'numeric' });
                                            } else {
                                                // In raw mode, dateValue is an ISO date string or Date object
                                                const date = new Date(dateValue);
                                                return date.toLocaleDateString(); // Format as 'MM/DD/YYYY' or your locale format
                                            }
                                        }}
                                    />
                                    <YAxis />
                                    <Tooltip
                                        labelFormatter={(dateStr) => {
                                            const date = new Date(dateStr);
                                            return date.toLocaleDateString();
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="price"
                                        name={`Prezzo (${valuta})`}
                                        stroke="#8884d8"
                                        activeDot={{ r: 8 }}
                                    />
                                    {/* Include the custom legend */}
                                    {maxPriceData && minPriceData && (
                                        <Legend
                                            verticalAlign="middle"
                                            align="right"
                                            layout="vertical"
                                            content={<CustomLegend />}
                                        />
                                    )}
                                </LineChart>
                            </div>
                        </div>
                    )}
                </Modal>

                {/* Modal for displaying the order history */}
                <Modal
                    title={orderHistoryModalTitle}
                    visible={isOrderHistoryModalVisible}
                    onCancel={() => setIsOrderHistoryModalVisible(false)}
                    footer={null}
                    width={1500}
                >
                    {orderHistoryLoading ? (
                        <div style={{ textAlign: "center", padding: "50px 0" }}>
                             <Spin
                    indicator={<LoadingOutlined spin />}
                    size="large"
                     tip="Caricamento impegni articolo..." />
                        </div>
                    ) : (
                        <div>
                            <Table
                                dataSource={orderHistoryData}
                                columns={orderHistoryColumns}
                                rowKey={(record, index) => index}
                                pagination={{ pageSize: 25 }}
                                scroll={{ x: "max-content" }}
                            />
                        </div>
                    )}
                </Modal>

                <Modal
                    title="Seleziona Colonne"
                    visible={isColumnSelectorVisible}
                    onOk={() => setIsColumnSelectorVisible(false)}
                    onCancel={() => setIsColumnSelectorVisible(false)}
                >
                    <Checkbox.Group
                        style={{ display: "flex", flexDirection: "column" }}
                        value={visibleDataColumns}
                        onChange={(checkedValues) => setVisibleDataColumns(checkedValues)}
                    >
                        {dataColumns.map(col => (
                            <Checkbox key={col.key} value={col.key}>
                                {col.title}
                            </Checkbox>
                        ))}
                    </Checkbox.Group>
                </Modal>
                {/* Modal for Displaying Today's Orders */}
                <Modal
                    title={todayOrdersModalTitle}
                    visible={isTodayOrdersModalVisible}
                    onCancel={() => setIsTodayOrdersModalVisible(false)}
                    footer={null}
                    width={1500}
                >
                    {todayOrdersLoading ? (
                        <div style={{ textAlign: "center", padding: "50px 0" }}>
                            <Spin
                    indicator={<LoadingOutlined spin />}
                    size="large"
                     tip="Caricamento ordini odierni..." />
                        </div>
                    ) : (
                        <div>
                            <Table
                                dataSource={todayOrdersData}
                                columns={todayOrdersColumns}
                                rowKey={(record, index) => index}
                                pagination={{ pageSize: 10 }}
                                scroll={{ x: "max-content" }}
                            />
                        </div>
                    )}
                </Modal>

                {/* Simulation Order Modal */}
                <Modal
                    title="Simulazione Ordine"
                    visible={isSimulationModalVisible}
                    onCancel={handleCloseSimulationModal}
                    footer={[
                        <Button key="cancel" onClick={handleCloseSimulationModal}>
                            Chiudi
                        </Button>,
                        <Button 
                            key="simulate" 
                            type="primary" 
                            onClick={handleSimulate}
                            loading={simulationLoading}
                            disabled={simulationLoading}
                        >
                            Simula
                        </Button>
                    ]}
                    width={1600}
                >
                    <div>
                        <div style={{ marginBottom: '20px' }}>
                            {simulationRows.map((row, index) => (
                                <div key={index} style={{ display: 'flex', marginBottom: '10px', alignItems: 'center' }}>
                                    <Input
                                        placeholder="Codice Articolo"
                                        value={row.code}
                                        onChange={(e) => handleSimulationRowChange(index, 'code', e.target.value)}
                                        style={{ marginRight: '10px', flex: 2 }}
                                        disabled={simulationLoading}
                                    />
                                    <Input
                                        placeholder="Quantità"
                                        type="number"
                                        value={row.quantity}
                                        onChange={(e) => handleSimulationRowChange(index, 'quantity', e.target.value)}
                                        style={{ marginRight: '10px', flex: 1 }}
                                        disabled={simulationLoading}
                                    />
                                    {simulationRows.length > 1 && (
                                        <Button
                                            type="text"
                                            danger
                                            icon={<CloseOutlined />}
                                            onClick={() => handleRemoveSimulationRow(index)}
                                            disabled={simulationLoading}
                                        />
                                    )}
                                </div>
                            ))}
                            <Button
                                type="dashed"
                                onClick={handleAddSimulationRow}
                                style={{ width: '100%', marginTop: '10px' }}
                                icon={<span>+</span>}
                                disabled={simulationLoading}
                            >
                                Aggiungi articolo
                            </Button>
                            
                            {/* Time Period Selector */}
                            <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                                <Typography.Title level={5}>Periodo di simulazione:</Typography.Title>
                                <Radio.Group 
                                    value={selectedTimePeriod}
                                    onChange={(e) => setSelectedTimePeriod(e.target.value)}
                                    disabled={simulationLoading}
                                >
                                    <Radio value="today">OGGI</Radio>
                                    <Radio value="mc">Mese corrente ({new Date().toLocaleDateString('it-IT', {month: 'long', year: 'numeric'})})</Radio>
                                    <Radio value="ms">Mese successivo ({new Date(new Date().setMonth(new Date().getMonth() + 1)).toLocaleDateString('it-IT', {month: 'long', year: 'numeric'})})</Radio>
                                    <Radio value="msa">Tra due mesi ({new Date(new Date().setMonth(new Date().getMonth() + 2)).toLocaleDateString('it-IT', {month: 'long', year: 'numeric'})})</Radio>
                                    <Radio value="mss">Oltre ({new Date(new Date().setMonth(new Date().getMonth() + 3)).toLocaleDateString('it-IT', {month: 'long', year: 'numeric'})}+)</Radio>
                                </Radio.Group>
                            </div>
                        </div>
                        
                        {simulationLoading && (
                            <div style={{ textAlign: 'center', margin: '20px 0' }}>
                                <Spin 
                                    indicator={<LoadingOutlined spin />} 
                                    size="large" 
                                    tip="Elaborazione simulazione in corso..." 
                                />
                            </div>
                        )}
                        
                        {simulationComplete && simulationResults.length > 0 && (
                            <div style={{ marginTop: '20px' }}>
                                <Typography.Title level={4}>Risultati della Simulazione</Typography.Title>
                                <Table
                                    dataSource={simulationResults}
                                    columns={simulationResultsColumns}
                                    rowKey="code"
                                    pagination={false}
                                    size="small"
                                    bordered
                                />
                            </div>
                        )}
                        
                        {simulationComplete && simulationResults.length === 0 && (
                            <div style={{ textAlign: 'center', margin: '20px 0' }}>
                                <Alert
                                    message="Nessun risultato"
                                    description="La simulazione non ha prodotto risultati. Controlla i codici articolo inseriti."
                                    type="info"
                                    showIcon
                                />
                            </div>
                        )}
                    </div>
                </Modal>

                {/* Kiosk Modal */}
                {renderKioskModal()}

            </div>
        </>
    );
};

export default ArticlesTable;
