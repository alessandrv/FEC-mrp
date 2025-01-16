// src/components/TopArticleCard.js

import React from "react";
import { Card } from "antd";
import { StockOutlined } from "@ant-design/icons";

const TopArticleCard = ({ data }) => {
    if (!data || data.length === 0) return null;

    const topArticle = data[0]; // Assuming the data is sorted descending

    return (
        <Card>
            <Card.Meta
                avatar={<StockOutlined style={{ fontSize: "32px", color: "#52c41a" }} />}
                title="Top Performant Article"
                description={
                    <>
                        <p><strong>Article Code:</strong> {topArticle.occ_arti}</p>
                        <p><strong>Description:</strong> {topArticle.article_description}</p>
                        <p><strong>Total Quantity Sold:</strong> {topArticle.total_occ_qmov}</p>
                    </>
                }
            />
        </Card>
    );
};

export default TopArticleCard;
