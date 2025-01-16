// src/components/RechartsLineChart.js

import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import axios from "axios";
import { Spin, message } from "antd";

const RechartsLineChart = () => {
    const [trendData, setTrendData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTrendData = async () => {
            try {
                const response = await axios.get("http://172.16.16.69:8000/stock_trends");
                setTrendData(response.data);
            } catch (error) {
                message.error("Failed to fetch stock trends.");
                console.error("Stock trends fetch error:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchTrendData();
    }, []);

    if (loading) {
        return <Spin tip="Loading Stock Trends..." />;
    }

    return (
        <ResponsiveContainer width="100%" height={200}>
            <LineChart
                data={trendData}
                margin={{
                    top: 20, right: 30, left: 20, bottom: 5,
                }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="stock_quantity" stroke="#8884d8" name="Stock Quantity" />
                {/* Add more lines if needed */}
            </LineChart>
        </ResponsiveContainer>
    );
};

export default RechartsLineChart;
