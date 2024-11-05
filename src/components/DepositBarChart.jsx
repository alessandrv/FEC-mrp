// src/components/DepositBarChart.js

import React from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell
} from "recharts";

const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#d0ed57", "#a4de6c", "#ff8042", "#ffbb28", "#ff7f50"];

const DepositBarChart = ({ data }) => {

    // Determine the maximum deposit to adjust scaling if needed
    const maxDeposit = Math.max(...data.map(depot => depot.total_deposit));

    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart
                data={data}
                margin={{
                    top: 20, right: 30, left: 20, bottom: 50,
                }}
            >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                    dataKey="dep_code" 
                    label={{ value: "Depot Code", position: "insideBottom", offset: -5 }}
                    angle={-45}
                    textAnchor="end"
                    interval={0}
                    height={60}
                />
                <YAxis 
                    label={{ value: "Total Deposit ($)", angle: -90, position: "insideLeft" }}
                    scale="sqrt" // Using square root scale to better display small values
                />
                <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, "Total Deposit"]} />
                <Legend verticalAlign="top" height={36} />
                <Bar dataKey="total_deposit" name="Total Deposit" >
                    {
                        data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))
                    }
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
};

export default DepositBarChart;
