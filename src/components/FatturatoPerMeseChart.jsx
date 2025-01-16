import React, { useState, useEffect } from "react";
import { DatePicker, Button, Radio } from "antd";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import axios from "axios";
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const FatturatoPerMeseChart = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [viewMode, setViewMode] = useState("monthly");

    const [dateRange, setDateRange] = useState([
        dayjs().startOf('year'),
        dayjs()
    ]);

    const formatDate = (date) => date.format("DD-MM-YYYY");

    const fetchData = async () => {
        if (!dateRange[0] || !dateRange[1]) return;

        setLoading(true);
        try {
            const endpoint = viewMode === "monthly" ? "fatturato_per_mese" :
                             viewMode === "yearly" ? "fatturato_per_anno" :
                             "fatturato_per_giorno"; // For daily view

            const start_date = formatDate(viewMode === "yearly" ? dateRange[0].startOf("year") : dateRange[0]);
            const end_date = formatDate(viewMode === "yearly" ? dateRange[1].endOf("year") : dateRange[1]);

            const response = await axios.get(`http://172.16.16.69:8000/${endpoint}`, {
                params: { start_date, end_date },
            });

            console.log("API response:", response.data);

            // Format data based on view mode
            const formattedData = response.data.map((item) => {
                if (viewMode === "daily") {
                    // Format full date for daily view
                    return {
                        period: dayjs(item.oct_data).format("YYYY-MM-DD"), // Assuming oct_data is in a parseable format
                        total_soldi: parseFloat(item.total_soldi),
                    };
                } else if (viewMode === "monthly") {
                    // Format as year-month for monthly view
                    return {
                        period: `${item.year}-${String(item.month).padStart(2, '0')}`,
                        total_soldi: parseFloat(item.total_soldi),
                    };
                } else {
                    // Use year for yearly view
                    return {
                        period: String(item.year),
                        total_soldi: parseFloat(item.total_soldi),
                    };
                }
            });

            setData(formattedData);
        } catch (error) {
            console.error("Error fetching data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [viewMode, dateRange]);

    const handleDateChange = (dates) => {
        setDateRange(dates);
    };

    const handleViewModeChange = (e) => {
        setViewMode(e.target.value);
    };

    return (
        <ResponsiveContainer width="100%" height={500}>
            <div style={{ display: "flex", gap: 10 }}>
                <Radio.Group onChange={handleViewModeChange} value={viewMode}>
                    <Radio.Button value="daily">Giornaliero</Radio.Button>
                    <Radio.Button value="monthly">Mensile</Radio.Button>
                    <Radio.Button value="yearly">Annuale</Radio.Button>
                </Radio.Group>

                <RangePicker
                    value={dateRange}
                    onChange={handleDateChange}
                    picker={viewMode === "yearly" ? "year" : "date"}
                    format={viewMode === "yearly" ? "YYYY" : "DD-MM-YYYY"}
                    allowClear={false}
                    style={{ flex: 1 }}
                />

                <Button type="primary" onClick={fetchData} loading={loading}>
                    Aggiorna dati
                </Button>
            </div>

            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" label={{ value: viewMode === "daily" ? "Giorno" : viewMode === "monthly" ? "Mese" : "Anno", position: "insideBottomRight", offset: -5 }} />
                <YAxis label={{ value: "Fatturato (€)", angle: -90, position: "insideLeft", offset: -15 }} />
                <Tooltip formatter={(value) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(value)} />
                <Line type="linear" dataKey="total_soldi" name="Fatturato" stroke="#0088FE" activeDot={{ r: 8 }} />
            </LineChart>
        </ResponsiveContainer>
    );
};

export default FatturatoPerMeseChart;
