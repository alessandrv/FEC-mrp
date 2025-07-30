import React, { useState, useEffect } from 'react';
import { Table, Spin, message, Input, Button, Tag, Tooltip, Typography, Card, Space, Modal, Checkbox } from 'antd';
import { SearchOutlined, ReloadOutlined, RiseOutlined, FallOutlined, LoadingOutlined, DownloadOutlined } from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend } from 'recharts';
import axios from 'axios';
import { API_BASE_URL } from './config';
import ExcelJS from 'exceljs';

const { Title, Text } = Typography;

const PriceList = () => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [searchText, setSearchText] = useState('');
    const [percentageFilters, setPercentageFilters] = useState({
        first_to_last: { min: '', max: '' },
        last_year_to_last: { min: '', max: '' },
        second_last_to_last: { min: '', max: '' }
    });

    // Price history modal state
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [chartLoading, setChartLoading] = useState(false);
    const [chartData, setChartData] = useState([]);
    const [rawChartData, setRawChartData] = useState([]);
    const [averageChartData, setAverageChartData] = useState([]);
    const [fifoChartData, setFifoChartData] = useState([]);
    const [currentFifoCost, setCurrentFifoCost] = useState(null);
    const [currentEffCost, setCurrentEffCost] = useState(null);
    const [maxPriceData, setMaxPriceData] = useState(null);
    const [minPriceData, setMinPriceData] = useState(null);
    const [valuta, setValuta] = useState(null);
    const [isAverage, setIsAverage] = useState(false);

    const fetchPriceList = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/price_list`);
            if (response.data.success) {
                setData(response.data.data);
                setFilteredData(response.data.data);
            } else {
                message.error('Errore nel caricamento dei dati');
            }
        } catch (error) {
            console.error('Error fetching price list:', error);
            message.error('Errore di connessione al server');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPriceList();
    }, []);

    useEffect(() => {
        if (data.length > 0) {
            applyFilters(searchText, percentageFilters);
        }
    }, [data]);

    const handleSearch = (value) => {
        setSearchText(value);
        applyFilters(value, percentageFilters);
    };

    const handlePercentageFilterChange = (filterType, field, value) => {
        const newFilters = {
            ...percentageFilters,
            [filterType]: {
                ...percentageFilters[filterType],
                [field]: value
            }
        };
        setPercentageFilters(newFilters);
        applyFilters(searchText, newFilters);
    };

    const applyFilters = (searchValue, percentageFilterValues) => {
        let filtered = data;

        // Apply search filter
        if (searchValue) {
            filtered = filtered.filter(item => 
                item.article_code.toLowerCase().includes(searchValue.toLowerCase())
            );
        }

        // Apply percentage filters
        Object.keys(percentageFilterValues).forEach(filterType => {
            const filter = percentageFilterValues[filterType];
            if (filter.min !== '' || filter.max !== '') {
                filtered = filtered.filter(item => {
                    const changeValue = item.changes[filterType];
                    const min = filter.min !== '' ? parseFloat(filter.min) : -Infinity;
                    const max = filter.max !== '' ? parseFloat(filter.max) : Infinity;
                    return changeValue >= min && changeValue <= max;
                });
            }
        });

        setFilteredData(filtered);
    };

    const clearAllFilters = () => {
        setSearchText('');
        setPercentageFilters({
            first_to_last: { min: '', max: '' },
            last_year_to_last: { min: '', max: '' },
            second_last_to_last: { min: '', max: '' }
        });
        setFilteredData(data);
    };

    const exportToExcel = async () => {
        try {
            const lastYear = new Date().getFullYear() - 1;
            const costoLastYear = `Costo al 31/12/${lastYear}`;
            
            // Create workbook and worksheet
            const workbook = new ExcelJS.Workbook();
            const worksheet = workbook.addWorksheet('Report Variazioni Costi');

            // Define headers in correct order
            const headers = [
                'Codice Articolo',
                'Descrizione', 
                'Valuta',
                'Costo Storico',
                costoLastYear,
                'Penultimo Costo',
                'Ultimo Costo',
                'Variazione Storico → Ultimo (%)',
                'Variazione Anno Scorso → Ultimo (%)',
                'Variazione Penultimo → Ultimo (%)'
            ];

            // Add header row
            const headerRow = worksheet.addRow(headers);
            
            // Style header row
            headerRow.eachCell((cell, colNumber) => {
                cell.fill = {
                    type: 'pattern',
                    pattern: 'solid',
                    fgColor: { argb: 'FF366092' } // Dark blue
                };
                cell.font = {
                    bold: true,
                    color: { argb: 'FFFFFFFF' } // White
                };
                cell.alignment = {
                    horizontal: 'center',
                    vertical: 'middle'
                };
                cell.border = {
                    top: { style: 'thin' },
                    bottom: { style: 'thin' },
                    left: { style: 'thin' },
                    right: { style: 'thin' }
                };
            });

            // Add data rows
            filteredData.forEach((item, index) => {
                const rowData = [
                    item.article_code,
                    item.description || '',
                    item.valuta,
                    item.first_price.price,
                    item.last_year_last_price.price,
                    item.second_last_price.price,
                    item.last_price.price,
                    item.changes.first_to_last / 100, // Convert percentage to decimal
                    item.changes.last_year_to_last / 100, // Convert percentage to decimal
                    item.changes.second_last_to_last / 100 // Convert percentage to decimal
                ];
                
                const dataRow = worksheet.addRow(rowData);
                
                // Style data row with alternating colors
                const isEvenRow = index % 2 === 0;
                dataRow.eachCell((cell, colNumber) => {
                    // Base styling
                    cell.fill = {
                        type: 'pattern',
                        pattern: 'solid',
                        fgColor: { argb: isEvenRow ? 'FFF2F2F2' : 'FFFFFFFF' } // Alternating colors
                    };
                    cell.border = {
                        top: { style: 'thin' },
                        bottom: { style: 'thin' },
                        left: { style: 'thin' },
                        right: { style: 'thin' }
                    };
                    cell.alignment = {
                        horizontal: 'center',
                        vertical: 'middle'
                    };

                    // Special formatting for percentage columns (columns 7, 8, 9 - 1-indexed)
                    if (colNumber >= 8) {
                        const percentageValue = rowData[colNumber - 1];
                        if (percentageValue > 0) {
                            // Positive percentage - red background
                            cell.fill.fgColor = { argb: 'FFFFE6E6' }; // Light red
                            cell.font = { 
                                color: { argb: 'FFCC0000' }, // Dark red
                                bold: true 
                            };
                        } else if (percentageValue < 0) {
                            // Negative percentage - green background
                            cell.fill.fgColor = { argb: 'FFE6FFE6' }; // Light green
                            cell.font = { 
                                color: { argb: 'FF006600' }, // Dark green
                                bold: true 
                            };
                        }
                        // Zero percentage keeps default styling
                    }

                    // Number formatting for cost columns (columns 4, 5, 6, 7 - 1-indexed)
                    if (colNumber >= 4 && colNumber <= 7) {
                        cell.numFmt = '#,##0.00';
                    }

                    // Percentage formatting for percentage columns
                    if (colNumber >= 8) {
                        cell.numFmt = '0.00%';
                    }
                });
            });

            // Set column widths
            worksheet.columns = [
                { key: 'A', width: 15 }, // Codice Articolo
                { key: 'B', width: 40 }, // Descrizione
                { key: 'C', width: 8 },  // Valuta
                { key: 'D', width: 15 }, // Costo Storico
                { key: 'E', width: 20 }, // Costo al 31/12/YYYY
                { key: 'F', width: 15 }, // Penultimo Costo
                { key: 'G', width: 15 }, // Ultimo Costo
                { key: 'H', width: 25 }, // Variazione Storico → Ultimo (%)
                { key: 'I', width: 30 }, // Variazione Anno Scorso → Ultimo (%)
                { key: 'J', width: 30 }  // Variazione Penultimo → Ultimo (%)
            ];

            // Generate filename with current date
            const currentDate = new Date().toISOString().split('T')[0];
            const filename = `Report_Variazioni_Costi_${currentDate}.xlsx`;

            // Save the file
            const buffer = await workbook.xlsx.writeBuffer();
            const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.click();
            window.URL.revokeObjectURL(url);

            message.success(`File Excel esportato: ${filename}`);
        } catch (error) {
            console.error('Error exporting to Excel:', error);
            message.error('Errore durante l\'esportazione del file Excel');
        }
    };

    // Price history modal functions
    const handleAPClick = (articleCode) => {
        // Open the modal and show loading spinner
        setIsModalVisible(true);
        setChartLoading(true);
        setModalTitle(`Storico prezzi per articolo: ${articleCode}`);
        setIsAverage(false); // Reset checkbox state
        setChartData([]); // Clear existing chart data
        setRawChartData([]);
        setAverageChartData([]);
        setFifoChartData([]);
        setCurrentFifoCost(null);
        setCurrentEffCost(null);
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
            // Fetch processed data from the backend
            const priceResponse = await axios.get(`${API_BASE_URL}/article_price`, {
                params: { article_code: articleCode },
            });

            const {
                rawData,
                averageData,
                fifoData,
                currentFifoCost: currentFifo,
                currentEffCost: currentEff,
                valuta: valutaData,
                maxPriceData: maxPrice,
                minPriceData: minPrice,
            } = priceResponse.data;

            if (rawData.length === 0) {
                message.info("No price data available for this article.");
                setIsModalVisible(false);
                setChartLoading(false);
                return;
            }

            // Set state variables
            setRawChartData(rawData);
            setAverageChartData(averageData);
            setFifoChartData(fifoData || []);
            setCurrentFifoCost(currentFifo);
            setCurrentEffCost(currentEff);
            setMaxPriceData(maxPrice);
            setMinPriceData(minPrice);
            setValuta(valutaData);
            
            // Call updateChartData directly with the current data
            updateChartData(false, rawData, fifoData, currentFifo, currentEff);
            setChartLoading(false);

        } catch (error) {
            message.error("Impossibile trovare storico prezzi.");
            console.error("Error fetching article price data:", error);
            setIsModalVisible(false);
            setChartLoading(false);
        }
    };

    const handleCheckboxChange = (e) => {
        setIsAverage(e.target.checked);
        updateChartData(e.target.checked);
    };

    const updateChartData = (average, rawData = null, fifoData = null, currentFifo = null, currentEff = null) => {
        // Use passed data or fall back to state variables
        const dataToUse = rawData || rawChartData;
        const fifoToUse = fifoData || fifoChartData;
        const currentFifoToUse = currentFifo || currentFifoCost;
        const currentEffToUse = currentEff || currentEffCost;
        
        if (average) {
            // In average mode, create combined dataset with averaged FIFO data
            const combinedAverageData = [...averageChartData];
            
            // Create monthly averaged FIFO data independently
            const fifoMonthlyData = {};
            fifoToUse.forEach(fifoItem => {
                const date = new Date(fifoItem.date);
                const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                
                if (!fifoMonthlyData[monthKey]) {
                    fifoMonthlyData[monthKey] = {
                        total: 0,
                        count: 0,
                        dates: []
                    };
                }
                fifoMonthlyData[monthKey].total += fifoItem.price;
                fifoMonthlyData[monthKey].count += 1;
                fifoMonthlyData[monthKey].dates.push(fifoItem.date);
            });
            
            // Add averaged FIFO data as independent data points
            Object.keys(fifoMonthlyData).forEach(monthKey => {
                const monthData = fifoMonthlyData[monthKey];
                const averageFifoPrice = monthData.total / monthData.count;
                
                // Always add as a new data point, don't try to merge with base price data
                combinedAverageData.push({
                    date: monthKey,
                    price: null, // Base price is null for FIFO-only months
                    quantity: 0,
                    valuta: valuta,
                    fifoPrice: averageFifoPrice
                });
            });
            
            // Add current FIFO cost as part of FIFO data (same color/line)
            if (currentFifoToUse) {
                const currentFifoDate = new Date(currentFifoToUse.date);
                const currentFifoMonthKey = `${currentFifoDate.getFullYear()}-${String(currentFifoDate.getMonth() + 1).padStart(2, '0')}`;
                
                const existingIndex = combinedAverageData.findIndex(item => item.date === currentFifoMonthKey);
                if (existingIndex >= 0) {
                    combinedAverageData[existingIndex].fifoPrice = currentFifoToUse.price;
                } else {
                    combinedAverageData.push({
                        date: currentFifoMonthKey,
                        price: null,
                        quantity: 0,
                        valuta: valuta,
                        fifoPrice: currentFifoToUse.price
                    });
                }
            }
            
            if (currentEffToUse) {
                const currentEffDate = new Date(currentEffToUse.date);
                const currentEffMonthKey = `${currentEffDate.getFullYear()}-${String(currentEffDate.getMonth() + 1).padStart(2, '0')}`;
                
                const existingIndex = combinedAverageData.findIndex(item => item.date === currentEffMonthKey);
                if (existingIndex >= 0) {
                    combinedAverageData[existingIndex].currentEff = currentEffToUse.price;
                } else {
                    combinedAverageData.push({
                        date: currentEffMonthKey,
                        price: null,
                        quantity: 0,
                        valuta: valuta,
                        currentEff: currentEffToUse.price
                    });
                }
            }
            
            // Sort by date
            combinedAverageData.sort((a, b) => new Date(a.date + '-01') - new Date(b.date + '-01'));
            
            setChartData(combinedAverageData);
        } else {
            // In raw mode, dates represent individual dates
            // Create combined dataset with FIFO data and current costs
            const combinedData = [...dataToUse];
            
            // Add FIFO data points (including current FIFO cost)
            fifoToUse.forEach(fifoItem => {
                const existingIndex = combinedData.findIndex(item => item.date === fifoItem.date);
                if (existingIndex >= 0) {
                    combinedData[existingIndex].fifoPrice = fifoItem.price;
                } else {
                    combinedData.push({
                        date: fifoItem.date,
                        price: null,
                        quantity: 0,
                        valuta: valuta,
                        fifoPrice: fifoItem.price
                    });
                }
            });
            
            // Add current FIFO cost as part of FIFO data (same color/line)
            if (currentFifoToUse) {
                const existingIndex = combinedData.findIndex(item => item.date === currentFifoToUse.date);
                if (existingIndex >= 0) {
                    combinedData[existingIndex].fifoPrice = currentFifoToUse.price;
                } else {
                    combinedData.push({
                        date: currentFifoToUse.date,
                        price: null,
                        quantity: 0,
                        valuta: valuta,
                        fifoPrice: currentFifoToUse.price
                    });
                }
            }
            
            // Add current effective cost
            if (currentEffToUse) {
                const existingIndex = combinedData.findIndex(item => item.date === currentEffToUse.date);
                if (existingIndex >= 0) {
                    combinedData[existingIndex].currentEff = currentEffToUse.price;
                } else {
                    combinedData.push({
                        date: currentEffToUse.date,
                        price: null,
                        quantity: 0,
                        valuta: valuta,
                        currentEff: currentEffToUse.price
                    });
                }
            }
            
            // Sort by date
            combinedData.sort((a, b) => new Date(a.date) - new Date(b.date));
            
            setChartData(combinedData);
        }
    };

    const formatPrice = (price, valuta) => {
        return `${price.toFixed(2)} ${valuta}`;
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('it-IT');
    };

    const renderPercentageChange = (change) => {
        if (change === 0) {
            return <Tag color="default">0%</Tag>;
        }
        
        const isPositive = change > 0;
        const color = isPositive ? 'red' : 'green';
        const icon = isPositive ? <RiseOutlined /> : <FallOutlined />;
        
        return (
            <Tag color={color} icon={icon}>
                {isPositive ? '+' : ''}{change}%
            </Tag>
        );
    };

    const columns = [
        {
            title: 'Codice Articolo',
            dataIndex: 'article_code',
            key: 'article_code',
            width: 150,
            fixed: 'left',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Descrizione',
            dataIndex: 'description',
            key: 'description',
            width: 300,
        },
        {
            title: 'Costo Storico',
            key: 'first_price',
            width: 200,
            render: (_, record) => (
                <div>
                    <div><strong>{formatPrice(record.first_price.price, record.valuta)}</strong></div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                        {formatDate(record.first_price.date)} ({record.first_price.quantity} pz)
                    </div>
                </div>
            ),
        },
        {
            title: `Costo al 31/12/${new Date().getFullYear() - 1}`,
            key: 'last_year_last_price',
            width: 200,
            render: (_, record) => (
                <div>
                    <div><strong>{formatPrice(record.last_year_last_price.price, record.valuta)}</strong></div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                        {formatDate(record.last_year_last_price.date)} ({record.last_year_last_price.quantity} pz)
                    </div>
                </div>
            ),
        },
        {
            title: 'Penultimo Costo',
            key: 'second_last_price',
            width: 200,
            render: (_, record) => (
                <div>
                    <div><strong>{formatPrice(record.second_last_price.price, record.valuta)}</strong></div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                        {formatDate(record.second_last_price.date)} ({record.second_last_price.quantity} pz)
                    </div>
                </div>
            ),
        },
        {
            title: 'Ultimo Costo',
            key: 'last_price',
            width: 200,
            render: (_, record) => (
                <div>
                    <div><strong>{formatPrice(record.last_price.price, record.valuta)}</strong></div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                        {formatDate(record.last_price.date)} ({record.last_price.quantity} pz)
                    </div>
                </div>
            ),
        },
        {
            title: 'Variazione Storico → Ultimo',
            key: 'first_to_last',
            width: 180,
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <div style={{ marginBottom: 8 }}>
                        <Input
                            placeholder="Min %"
                            value={percentageFilters.first_to_last.min}
                            onChange={(e) => handlePercentageFilterChange('first_to_last', 'min', e.target.value)}
                            style={{ marginBottom: 4 }}
                        />
                        <Input
                            placeholder="Max %"
                            value={percentageFilters.first_to_last.max}
                            onChange={(e) => handlePercentageFilterChange('first_to_last', 'max', e.target.value)}
                        />
                    </div>
                   
                </div>
            ),
            render: (_, record) => (
                <Tooltip title={`Dal primo prezzo (${formatDate(record.first_price.date)}) all'ultimo prezzo (${formatDate(record.last_price.date)})`}>
                    {renderPercentageChange(record.changes.first_to_last)}
                </Tooltip>
            ),
        },
        {
            title: 'Variazione Anno Scorso → Ultimo',
            key: 'last_year_to_last',
            width: 180,
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <div style={{ marginBottom: 8 }}>
                        <Input
                            placeholder="Min %"
                            value={percentageFilters.last_year_to_last.min}
                            onChange={(e) => handlePercentageFilterChange('last_year_to_last', 'min', e.target.value)}
                            style={{ marginBottom: 4 }}
                        />
                        <Input
                            placeholder="Max %"
                            value={percentageFilters.last_year_to_last.max}
                            onChange={(e) => handlePercentageFilterChange('last_year_to_last', 'max', e.target.value)}
                        />
                    </div>
                    
                </div>
            ),
            render: (_, record) => (
                <Tooltip title={`Dall'ultimo prezzo dell'anno scorso (${formatDate(record.last_year_last_price.date)}) all'ultimo prezzo (${formatDate(record.last_price.date)})`}>
                    {renderPercentageChange(record.changes.last_year_to_last)}
                </Tooltip>
            ),
        },
        {
            title: 'Variazione Penultimo → Ultimo',
            key: 'second_last_to_last',
            width: 180,
            filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
                <div style={{ padding: 8 }}>
                    <div style={{ marginBottom: 8 }}>
                        <Input
                            placeholder="Min %"
                            value={percentageFilters.second_last_to_last.min}
                            onChange={(e) => handlePercentageFilterChange('second_last_to_last', 'min', e.target.value)}
                            style={{ marginBottom: 4 }}
                        />
                        <Input
                            placeholder="Max %"
                            value={percentageFilters.second_last_to_last.max}
                            onChange={(e) => handlePercentageFilterChange('second_last_to_last', 'max', e.target.value)}
                        />
                    </div>
                   
                </div>
            ),
            render: (_, record) => (
                <Tooltip title={`Dal penultimo prezzo (${formatDate(record.second_last_price.date)}) all'ultimo prezzo (${formatDate(record.last_price.date)})`}>
                    {renderPercentageChange(record.changes.second_last_to_last)}
                </Tooltip>
            ),
        },
        {
            title: 'Azioni',
            key: 'actions',
            width: 100,
            fixed: 'right',
            render: (_, record) => (
                <Button 
                    type="primary" 
                    size="small"
                    onClick={() => handleAPClick(record.article_code)}
                >
                    Storico
                </Button>
            ),
        },
    ];

    // Custom Legend Component
    const CustomLegend = () => {
        return (
            <div style={{ 
                display: "flex", 
                flexDirection: "column", 
                gap: "15px"
            }}>
                <div>
                    <strong>Valuta:</strong> {valuta || 'N/A'}
                </div>
                
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {maxPriceData && maxPriceData.price && (
                        <div style={{ fontSize: "12px" }}>
                            <strong>Prezzo Max:</strong><br/>
                            {maxPriceData.price.toFixed(2)} - {new Date(maxPriceData.date).toLocaleDateString()}
                        </div>
                    )}
                    {minPriceData && minPriceData.price && (
                        <div style={{ fontSize: "12px" }}>
                            <strong>Prezzo Min:</strong><br/>
                            {minPriceData.price.toFixed(2)} - {new Date(minPriceData.date).toLocaleDateString()}
                        </div>
                    )}
                    {currentFifoCost && currentFifoCost.price && (
                        <div style={{ fontSize: "12px" }}>
                            <strong>Costo FIFO Attuale:</strong><br/>
                            {currentFifoCost.price.toFixed(2)} - {new Date(currentFifoCost.date).toLocaleDateString()}
                        </div>
                    )}
                    {currentEffCost && currentEffCost.price && (
                        <div style={{ fontSize: "12px" }}>
                            <strong>Costo Effettivo:</strong><br/>
                            {currentEffCost.price.toFixed(2)} - {new Date(currentEffCost.date).toLocaleDateString()}
                        </div>
                    )}
                </div>

                <div style={{ textAlign: "center" }}>
                    <Checkbox
                        checked={isAverage}
                        onChange={handleCheckboxChange}
                    >
                        Media per mese
                    </Checkbox>
                </div>
            </div>
        );
    };

    return (
        <div style={{ padding: '20px' }}>
            <Card>
                <div style={{ marginBottom: '20px' }}>
                    <Title level={2}>Report Variazioni Costi</Title>
                    
                </div>

                <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <Input
                        placeholder="Cerca per codice articolo..."
                        value={searchText}
                        onChange={(e) => handleSearch(e.target.value)}
                        style={{ width: '300px' }}
                        prefix={<SearchOutlined />}
                    />
                    <Button 
                        icon={<ReloadOutlined />} 
                        onClick={fetchPriceList}
                        loading={loading}
                    >
                        Aggiorna
                    </Button>
                    <Button 
                        onClick={clearAllFilters}
                        size="small"
                    >
                        Cancella Filtri
                    </Button>
                    <Button 
                        type="primary"
                        icon={<DownloadOutlined />}
                        onClick={exportToExcel}
                        disabled={filteredData.length === 0}
                    >
                        Export Excel
                    </Button>
                    <Text type="secondary">
                        {filteredData.length} articoli trovati
                    </Text>
                </div>

                <Table
                    columns={columns}
                    dataSource={filteredData}
                    rowKey="article_code"
                    loading={loading}
                    scroll={{ x: 1500 }}
                    pagination={{
                        pageSize: 50,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total, range) => 
                            `${range[0]}-${range[1]} di ${total} articoli`,
                    }}
                    size="small"
                />

                {/* Price History Modal */}
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
                        setFifoChartData([]);
                        setCurrentFifoCost(null);
                        setCurrentEffCost(null);
                        setIsAverage(false);
                        setValuta(null);
                    }}
                    footer={null}
                    width={1100}
                    style={{ top: '50%', transform: 'translateY(-50%)' }}
                >
                    {chartLoading ? (
                        <div style={{ textAlign: "center", padding: "50px 0" }}>
                            <Spin
                                indicator={<LoadingOutlined spin />}
                                size="large" 
                                tip="Caricamento storico prezzi..." 
                            />
                        </div>
                    ) : chartData && chartData.length > 0 ? (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "600px" }}>
                            <div style={{ display: "flex", gap: "20px" }}>
                                {/* Charts Section */}
                                <div style={{ display: "flex", flexDirection: "column", gap: "20px", flex: 1 }}>
                                    {/* Base Price Chart */}
                                    <div>
                                        <h3 style={{ textAlign: "center", marginBottom: "10px" }}>Prezzo Base</h3>
                                        <LineChart
                                            width={800}
                                            height={300}
                                            data={isAverage ? averageChartData.filter(item => item.price !== null) : chartData.filter(item => item.price !== null)}
                                            margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis
                                                dataKey="date"
                                                angle={-45}
                                                textAnchor="end"
                                                tickFormatter={(dateValue) => {
                                                    if (isAverage) {
                                                        const date = new Date(dateValue + '-01');
                                                        return date.toLocaleString('default', { month: 'short', year: 'numeric' });
                                                    } else {
                                                        const date = new Date(dateValue);
                                                        return date.toLocaleDateString();
                                                    }
                                                }}
                                            />
                                            <YAxis />
                                            <RechartsTooltip
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
                                        </LineChart>
                                    </div>

                                    {/* FIFO Chart */}
                                    <div>
                                        <h3 style={{ textAlign: "center", marginBottom: "10px" }}>Prezzo FIFO</h3>
                                        <LineChart
                                            width={800}
                                            height={300}
                                            data={chartData.filter(item => item.fifoPrice !== undefined)}
                                            margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis
                                                dataKey="date"
                                                angle={-45}
                                                textAnchor="end"
                                                tickFormatter={(dateValue) => {
                                                    if (isAverage) {
                                                        const date = new Date(dateValue + '-01');
                                                        return date.toLocaleString('default', { month: 'short', year: 'numeric' });
                                                    } else {
                                                        const date = new Date(dateValue);
                                                        return date.toLocaleDateString();
                                                    }
                                                }}
                                            />
                                            <YAxis />
                                            <RechartsTooltip
                                                labelFormatter={(dateStr) => {
                                                    const date = new Date(dateStr);
                                                    return date.toLocaleDateString();
                                                }}
                                            />
                                            {fifoChartData && fifoChartData.length > 0 && (
                                                <Line
                                                    type="monotone"
                                                    dataKey="fifoPrice"
                                                    name="Prezzo FIFO"
                                                    stroke="#ff7300"
                                                    activeDot={{ r: 1}}
                                                />
                                            )}
                                        </LineChart>
                                    </div>
                                </div>

                                {/* Legend Section - Right Side */}
                                <div style={{ width: "250px", flexShrink: 0, display: "flex", alignItems: "center" }}>
                                    <CustomLegend />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div style={{ textAlign: "center", padding: "50px 0" }}>
                            <p>Nessun dato disponibile per questo articolo.</p>
                        </div>
                    )}
                </Modal>
            </Card>
        </div>
    );
};

export default PriceList; 