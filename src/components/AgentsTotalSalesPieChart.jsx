import React, { useMemo } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Empty } from "antd";

const COLORS = [
    "#0088FE", "#00C49F", "#FFBB28", "#FF8042",
    "#AF19FF", "#FF4560", "#1E3A5F", "#2E8B57",
    "#FFD700", "#8A2BE2", "#A52A2A", "#5F9EA0",
    "#D2691E", "#8B008B", "#556B2F", "#20B2AA",
    "#4B0082", "#B22222", "#FF69B4", "#7FFF00"
];

const AgentsTotalSalesPieChart = ({ dataVendite, dataFatturato }) => {
    // Generate color mapping for consistent coloring
    const agentColorMap = useMemo(() => {
        const uniqueAgents = new Set([
            ...(dataVendite?.map(agent => agent.des_agente) || []),
            ...(dataFatturato?.map(agent => agent.des_agente) || [])
        ]);

        const colorMap = {};
        Array.from(uniqueAgents).forEach((agent, index) => {
            colorMap[agent] = COLORS[index % COLORS.length];
        });
        return colorMap;
    }, [dataVendite, dataFatturato]);

    // Combine unique agent names from both datasets for the unified legend
    const combinedLegendData = useMemo(() => {
        return Object.keys(agentColorMap).map(name => ({
            name,
            color: agentColorMap[name]
        }));
    }, [agentColorMap]);

    // Early return if there’s no valid data to display
    if (
        (!dataVendite || dataVendite.length === 0 || dataVendite.every(agent => agent.total_occ_qmov === 0)) &&
        (!dataFatturato || dataFatturato.length === 0 || dataFatturato.every(agent => agent.total_soldi === 0))
    ) {
        return <Empty description="Nessun dato disponibile." />;
    }

    // Transform data for the Pie charts and filter out zero values
    const pieData = dataVendite
        .map(agent => ({
            name: agent.des_agente,
            value: agent.total_occ_qmov
        }))
        .filter(item => item.value > 0);

    const pieData2 = dataFatturato
        .map(agent => ({
            name: agent.des_agente,
            value: agent.total_soldi
        }))
        .filter(item => item.value > 0);

    return (
        <ResponsiveContainer width="100%" height={500}>
            <PieChart>
                {/* Titles for each Pie */}
                <text x="25%" y="5%"  textAnchor="middle" dominantBaseline="middle" fontSize={16} fontWeight="bold">
                    Quantità Venduta
                </text>
                <text x="75%" y="5%" textAnchor="middle" dominantBaseline="middle" fontSize={16} fontWeight="bold">
                    Totale Fatturato
                </text>

                <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="25%"
                    cy="50%"
                   
                    outerRadius={150}
                    label
                >
                    {pieData.map((entry, index) => (
                        <Cell key={`cell-vendite-${index}`} fill={agentColorMap[entry.name]} />
                    ))}
                </Pie>
                
                <Pie
                    data={pieData2}
                    dataKey="value"
                    nameKey="name"
                    cx="75%"
                    cy="50%"
                   
                    outerRadius={150}
                    label
                >
                    {pieData2.map((entry, index) => (
                        <Cell key={`cell-fatturato-${index}`} fill={agentColorMap[entry.name]} />
                    ))}
                </Pie>

                <Tooltip />
                
                {/* Unified Legend */}
                <Legend
                    payload={combinedLegendData.map((item) => ({
                        value: item.name,
                        type: "square",
                        color: item.color
                    }))}
                />
            </PieChart>
        </ResponsiveContainer>
    );
};

export default AgentsTotalSalesPieChart;
