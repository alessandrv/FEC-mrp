import React, { useState, useMemo, useEffect } from "react";
import { Input, Empty, Select, Radio, Tag } from "antd";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    Cell
} from "recharts";

const { Search } = Input;
const { Option } = Select;

const COLORS = [
    "#0088FE", "#00C49F", "#FFBB28", "#FF8042",
    "#AF19FF", "#FF4560", "#00E396", "#775DD0",
    "#FEB019", "#FF66C3"
];

const ArticlesWithDescriptionBarChart = ({ data }) => {
    const [searchTerm, setSearchTerm] = useState("");
    const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
    const [selectedCategories, setSelectedCategories] = useState(["Tutto"]);
    const [valueType, setValueType] = useState("total_occ_qmov");
    const [barCount, setBarCount] = useState(20);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedTerm(searchTerm);
        }, 300);

        return () => {
            clearTimeout(handler);
        };
    }, [searchTerm]);

    const onSearch = (value) => {
        setSearchTerm(value.trim());
    };

    const handleCategoryChange = (value) => {
        if (value.includes("Tutto") && value.length > 1 && value[0] !== "Tutto") {
            setSelectedCategories(["Tutto"]);
        }
        else  if (value.includes("Tutto") && value.length > 1) {
            // If "Tutto" is selected along with other categories, remove other categories and keep only "Tutto"
            setSelectedCategories(value.filter(category => category !== "Tutto"));
        } else {
            // If another category is selected while "Tutto" is active, remove "Tutto" and add selected categories
            setSelectedCategories(value);
        }
    };

    const handleValueTypeChange = (e) => {
        setValueType(e.target.value);
    };

    const handleBarCountChange = (value) => {
        setBarCount(value);
    };

    const categories = useMemo(() => {
        const uniqueCategories = [...new Set(data.map(item => item.categoria))].sort();
        return ["Tutto", ...uniqueCategories];
    }, [data]);

    const filteredData = useMemo(() => {
        let filtered = data;

        if (debouncedTerm !== "") {
            const lowerCaseTerm = debouncedTerm.toLowerCase();
            filtered = filtered.filter(article =>
                (article.occ_arti && article.occ_arti.toLowerCase().includes(lowerCaseTerm)) || 
                (article.article_description && article.article_description.toLowerCase().includes(lowerCaseTerm))
            );
        }

        if (selectedCategories.length > 0 && !selectedCategories.includes("Tutto")) {
            filtered = filtered.filter(article => selectedCategories.includes(article.categoria));
        }

        return filtered
            .map(article => ({
                ...article,
                adjustedValue: valueType === "total_soldi_netto"
                    ? parseFloat(article.total_soldi) * 0.78
                    : parseFloat(article[valueType])
            }))
            .sort((a, b) => b.adjustedValue - a.adjustedValue)
            .slice(0, barCount);
    }, [data, debouncedTerm, selectedCategories, valueType, barCount]);

    const chartData = useMemo(() => {
        return filteredData.map((article, index) => ({
            key: index,
            occ_arti: article.occ_arti,
            value: article.adjustedValue,
            article_description: article.article_description,
        }));
    }, [filteredData]);

    return (
        <ResponsiveContainer width="100%" height={500}>
            <div style={{ marginBottom: 20, display: "flex", gap: 10 }}>
                <Search
                    placeholder="Filtra per codice o descrizione"
                    allowClear
                    enterButton="Cerca"
                    size="middle"
                    onSearch={onSearch}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{ flex: 1 }}
                />
                <Select
                    mode="multiple"
                    placeholder="Seleziona categorie"
                    value={selectedCategories}
                    onChange={handleCategoryChange}
                    dropdownRender={menu => (
                        <>
                            {menu}
                            <div style={{ padding: '8px', borderTop: '1px solid #e8e8e8' }}>
                                <span>Selezionato:</span>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '5px' }}>
                                    {selectedCategories.map(category => (
                                        <Tag
                                            key={category}
                                            color="blue"
                                            closable
                                            onClose={() => handleCategoryChange(selectedCategories.filter(cat => cat !== category))}
                                        >
                                            {category}
                                        </Tag>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                    style={{ width: 200, height: "32px", overflow: "hidden" }}
                >
                    {categories.map(category => (
                        <Option key={category} value={category}>{category}</Option>
                    ))}
                </Select>
                <Radio.Group
                    onChange={handleValueTypeChange}
                    value={valueType}
                >
                    <Radio.Button value="total_occ_qmov">Quantità Venduta</Radio.Button>
                    <Radio.Button value="total_soldi">Lordo</Radio.Button>
                    <Radio.Button value="total_soldi_netto">Netto</Radio.Button>
                </Radio.Group>
                <Select
                    value={barCount}
                    onChange={handleBarCountChange}
                    style={{ width: 100 }}
                    placeholder="Barre da mostrare"
                >
                    {[20, 40, 60, 80, 100].map(count => (
                        <Option key={count} value={count}>{count} Barre</Option>
                    ))}
                </Select>
            </div>

            {chartData.length > 0 ? (
                <BarChart
                    data={chartData}
                    margin={{
                        top: 20, right: 30, left: 20, bottom: 40
                    }}
                >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                        dataKey="occ_arti"
                        angle={-45}
                        textAnchor="end"
                        interval={0}
                        height={60}
                    />
                    <YAxis
                        label={{
                            value: valueType === "total_occ_qmov"
                                ? "Totale quantità venduta"
                                : valueType === "total_soldi_netto"
                                ? "Totale vendite netto (€)"
                                : "Totale vendite lordo (€)",
                            angle: -90,
                            position: "insideLeft"
                        }}
                        domain={[0, (dataMax) => Math.ceil(dataMax / 10) * 10]}
                    />
                    <Tooltip
                        formatter={(value) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(value)}
                        content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                                const data = payload[0].payload;
                                return (
                                    <div style={{ backgroundColor: '#fff', border: '1px solid #ccc', padding: '10px' }}>
                                        <p><strong>Codice articolo:</strong> {data.occ_arti}</p>
                                        <p><strong>Descrizione:</strong> {data.article_description}</p>
                                        <p><strong>{valueType === "total_occ_qmov" ? "Totale quantità venduta:" : valueType === "total_soldi_netto" ? "Totale vendite netto (€):" : "Totale vendite lordo (€):"}</strong> {new Intl.NumberFormat('it-IT').format(data.value)}</p>
                                    </div>
                                );
                            }
                            return null;
                        }}
                    />
                    <Legend />
                    <Bar dataKey="value" name={valueType === "total_occ_qmov" ? "Totale quantità venduta" : valueType === "total_soldi_netto" ? "Totale vendite netto (€)" : "Totale vendite lordo (€)"}>
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Bar>
                </BarChart>
            ) : (
                <Empty description="Nessun articolo corrisponde ai criteri di ricerca." />
            )}
        </ResponsiveContainer>
    );
};

export default ArticlesWithDescriptionBarChart;
