// src/components/AgentArticleSalesChart.js

import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const AgentArticleSalesChart = ({ data }) => {
    // Transform data to group by agent
    const groupedData = data.reduce((acc, curr) => {
        const agent = curr.des_agente;
        if (!acc[agent]) {
            acc[agent] = { des_agente: agent };
        }
        acc[agent][curr.occ_arti] = curr.total_occ_qmov;
        return acc;
    }, {});

    const chartData = Object.values(groupedData);

    // Get unique articles
    const articles = [...new Set(data.map(item => item.occ_arti))];

    const colors = [
        "#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#8dd1e1",
        "#a4de6c", "#d0ed57", "#ffc0cb", "#ffbb28", "#00C49F"
    ];

    return (
        <ResponsiveContainer width="100%" height={400}>
            <BarChart
                data={chartData}
                margin={{
                    top: 20, right: 30, left: 20, bottom: 5,
                }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="des_agente" />
                <YAxis />
                <Tooltip />
                <Legend />
                {articles.map((article, index) => (
                    <Bar key={article} dataKey={article} fill={colors[index % colors.length]} name={article} />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
};

export default AgentArticleSalesChart;
