import React, { useEffect } from 'react';
import ReactECharts from 'echarts-for-react';

const ForceNodeGraph = () => {
  // Define the nodes and links for the graph using the provided data
  const data = {
    "nodes": [
      { "name": "Party", "category": "People" },
      { "name": "Crystal Caverns", "category": "Location" },
      { "name": "Sunken Ruins of Eldoria", "category": "Location" },
      { "name": "Fire Peaks", "category": "Location" },
      { "name": "Central Convergence Point", "category": "Location" },
      { "name": "Cultists", "category": "People" },
      { "name": "Verdant Circle", "category": "Group" },
      { "name": "Elder Branwyn", "category": "Person" },
      { "name": "Kit’s Sending Stone", "category": "Item" },
      { "name": "Whispering Wood", "category": "Location" },
      { "name": "Mistress Sable", "category": "Person" },
      { "name": "Nighthaven", "category": "Location" },
      { "name": "Heart of the Verdant Plains", "category": "Location" },
      { "name": "Ruins of the Old Capitol", "category": "Location" },
      { "name": "Azure Bay", "category": "Location" },
      { "name": "Miners", "category": "People" },
      { "name": "Magical Beasts", "category": "Creatures" },
      { "name": "Pylon", "category": "Item" },
      { "name": "Sewer Beasts", "category": "Creatures" },
      { "name": "Sewers", "category": "Location" },
      { "name": "Hidden Chamber", "category": "Location" },
      { "name": "Cultist Leaders", "category": "People" },
      { "name": "Unique Cult Leaders", "category": "People" }
    ],
    "links": [
      { "source": "Party", "target": "Crystal Caverns", "relationship": "Investigates" },
      { "source": "Party", "target": "Sunken Ruins of Eldoria", "relationship": "Investigates" },
      { "source": "Party", "target": "Fire Peaks", "relationship": "Investigates" },
      { "source": "Party", "target": "Cultist Leaders", "relationship": "Confronts" },
      { "source": "Party", "target": "Pylon", "relationship": "Deactivates" },
      { "source": "Party", "target": "Central Convergence Point", "relationship": "Secures" },
      { "source": "Party", "target": "Sewer Beasts", "relationship": "Fights" },
      { "source": "Party", "target": "Sewers", "relationship": "Navigates" },
      { "source": "Party", "target": "Mistress Sable", "relationship": "Follows directions from" },
      { "source": "Party", "target": "Cultist Patrols", "relationship": "Faces off against" },
      { "source": "Party", "target": "Unique Cult Leaders", "relationship": "Faces off against" },
      { "source": "Party", "target": "Miners", "relationship": "Enlists help from" },
      { "source": "Party", "target": "Magical Beasts", "relationship": "Enlists help from" },
      { "source": "Verdant Circle", "target": "Whispering Wood", "relationship": "Guards" },
      { "source": "Verdant Circle", "target": "Heart of the Verdant Plains", "relationship": "Protects" },
      { "source": "Verdant Circle", "target": "Kit’s Sending Stone", "relationship": "Provides guidance via" },
      { "source": "Mistress Sable", "target": "Nighthaven", "relationship": "Provides intelligence for" },
      { "source": "Mistress Sable", "target": "Central Convergence Point", "relationship": "Coordinates search for" },
      { "source": "Cultists", "target": "Obelisks", "relationship": "Guard" },
      { "source": "Cultist Patrols", "target": "Obelisk Locations", "relationship": "Found at" },
      { "source": "Hidden Chamber", "target": "Pylon", "relationship": "Contains" },
      { "source": "Heart of the Verdant Plains", "target": "Central Convergence Point", "relationship": "Potential location for" },
      { "source": "Ruins of the Old Capitol", "target": "Central Convergence Point", "relationship": "Potential location for" },
      { "source": "Azure Bay", "target": "Central Convergence Point", "relationship": "Potential location for" },
      { "source": "Elder Branwyn", "target": "Verdant Circle", "relationship": "Leads" }
    ]
  };

  // ECharts options configuration
  const getOption = () => {
    return {
      tooltip: {},
      legend: [{
        data: ['People', 'Group', 'Location', 'Item', 'Creatures']
      }],
      series: [{
        type: 'graph',
        layout: 'force',
        categories: [
          { name: 'People' },
          { name: 'Group' },
          { name: 'Location' },
          { name: 'Item' },
          { name: 'Creatures' }
        ],
        data: data.nodes.map(node => ({
          name: node.name,
          category: node.category,
          symbolSize: 50
        })),
        links: data.links.map(link => ({
          source: link.source,
          target: link.target,
          label: {
            show: true,
            formatter: link.relationship,
          }
        })),
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}', // Display node names
        },
        force: {
          repulsion: 1000, // Adjust the distance between nodes
          edgeLength: [50, 150] // Min and max distance between nodes
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        edgeLabel: {
          show: true,
          formatter: function (params) {
            return params.data.label.formatter;
          }
        }
      }]
    };
  };

  return (
    <div>
      <ReactECharts
        option={getOption()}
        style={{ height: '600px', width: '900px' }}
      />
    </div>
  );
};

export default ForceNodeGraph;
