import React, { useEffect, useState } from 'react';
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
          name: node.id,
          category: node.category,
          symbolSize: 50,
        })),
        links: data2.links.map(link => ({
          source: link.source,
          target: link.target,
          label: {
            show: true,
            formatter: link.category,
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
        edgeLabel: {
          show: true,
          formatter: function (params) {
            return params.data.label.formatter;
          },
        },
      }],
    };
  };

  return (
    <div>
      <ReactECharts
        option={getOption()}
        style={{ height: '1000px', width: '1200px' }}
      />
    </div>
  );
};

export default ForceNodeGraph;
