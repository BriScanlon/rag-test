import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';

const ForceNodeGraph = ({ data2 }) => {
  const [categories, setCategories] = useState([]);

  // Extract unique categories from the data nodes
  useEffect(() => {
    const uniqueCategories = [...new Set(data2.nodes.map(node => node.category))];
    setCategories(uniqueCategories);
  }, [data2]);

  const getOption = () => {
    return {
      tooltip: {},
      legend: [{
        data: categories,  // Use the dynamic categories from the state
      }],
      series: [{
        type: 'graph',
        layout: 'force',
        categories: categories.map(category => ({ name: category })),
        data: data2.nodes.map(node => ({
          name: node.name,
          category: node.category,
          symbolSize: 50,
        })),
        links: data2.links.map(link => ({
          source: link.source,
          target: link.target,
          label: {
            show: true,
            formatter: link.relation,
          },
        })),
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}', // Display node names
        },
        force: {
          repulsion: 1000,  // Adjust the distance between nodes
          edgeLength: [50, 150],  // Min and max distance between nodes
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3,
        },
      }],
    };
  };

  return (

    <ReactECharts
      option={getOption()}
      style={{ height: '100%', width: '100%' }}
    />

  );
};

export default ForceNodeGraph;