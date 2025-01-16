// src/components/RechartsParetoChart.js

import React, { useMemo } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Line,
} from "recharts";

const RechartsParetoChart = ({ data }) => {
    // Calculate cumulative percentage
    const totalSales = useMemo(() => data.reduce((acc, article) => acc + article.total_sales, 0), [data]);

    const paretoData = useMemo(() => {
        let cumulative = 0;
        return data.map(article => {
            cumulative += article.total_sales;
            return { ...article, cumulative_percentage: ((cumulative / totalSales) * 100).toFixed(2) };
        });
    }, [data, totalSales]);

    return (
        <ResponsiveContainer width="100%" height={200}>
            <BarChart
                data={paretoData}
                margin={{
                    top: 20, right: 50, left: 20, bottom: 20,
                }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                    dataKey="c_articolo" 
                    label={{ value: "Article Code", position: "insideBottom", offset: -5 }}
                />
                <YAxis yAxisId="left" label={{ value: "Total Sales ($)", angle: -90, position: "insideLeft" }} />
                <YAxis yAxisId="right" orientation="right" label={{ value: "Cumulative %", angle: -90, position: "insideRight" }} />
                <Tooltip formatter={(value, name) => {
                    if (name === "cumulative_percentage") {
                        return [`${value}%`, name.replace('_', ' ').toUpperCase()];
                    }
                    return [`$${value.toLocaleString()}`, name.replace('_', ' ').toUpperCase()];
                }} />
                <Legend verticalAlign="top" height={36} />
                <Bar yAxisId="left" dataKey="total_sales" name="Total Sales" fill="#8884d8" />
                <Line yAxisId="right" type="monotone" dataKey="cumulative_percentage" name="Cumulative %" stroke="#ff7300" />
            </BarChart>
        </ResponsiveContainer>
    );
};

export default RechartsParetoChart;
