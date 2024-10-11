import React, { useEffect } from 'react';
import ReactECharts from 'echarts-for-react';

const ForceNodeGraph = () => {
  // Define the nodes and links for the force graph
  const nodes = [
    { id: 'ex:clinical_pharmacist', name: 'Clinical Pharmacist' },
    { id: 'ex:patient_care_units', name: 'Patient Care Units' },
    { id: 'ex:improvement_efforts', name: 'Improvement Efforts' },
    { id: 'ex:twice-daily_pickups', name: 'Twice-Daily Pickups' },
    { id: 'ex:discontinued_medications', name: 'Discontinued Medications' },
    { id: 'ex:verification_screen', name: 'Verification Screen' },
    { id: 'ex:patient_specific_unit_doses', name: 'Patient-Specific Unit Doses' },
    { id: 'ex:barcode_scanning', name: 'Barcode Scanning' },
    { id: 'ex:patient_verification', name: 'Patient Verification' },
    { id: 'ex:single-unit_doses', name: 'Single-Unit Doses' },
    { id: 'ex:multi-dose_vials', name: 'Multi-Dose Vials' }
  ];

  const links = [
    { source: 'ex:clinical_pharmacist', target: 'ex:patient_care_units', relationship: 'assignedTo' },
    { source: 'ex:clinical_pharmacist', target: 'ex:improvement_efforts', relationship: 'plannedBy' },
    { source: 'ex:clinical_pharmacist', target: 'ex:twice-daily_pickups', relationship: 'scheduledBy' },
    { source: 'ex:twice-daily_pickups', target: 'ex:discontinued_medications', relationship: 'forDiscontinuedMedications' },
    { source: 'ex:verification_screen', target: 'ex:clinical_pharmacist', relationship: 'usedFor' },
    { source: 'ex:patient_specific_unit_doses', target: 'ex:pharmacy', relationship: 'preparedBy' },
    { source: 'ex:patient_specific_unit_doses', target: 'ex:multi-dose_vials', relationship: 'replacesMultiDoseVials' },
    { source: 'ex:barcode_scanning', target: 'ex:clinical_pharmacist', relationship: 'usedFor' },
    { source: 'ex:barcode_scanning', target: 'ex:patient_verification', relationship: 'involves' },
    { source: 'ex:single-unit_doses', target: 'ex:pharmacy', relationship: 'preparedBy' },
    { source: 'ex:single-unit_doses', target: 'ex:multi-dose_vials', relationship: 'replacesMultiDoseVials' }
  ];

  // Convert the nodes into the format required by ECharts
  const formattedNodes = nodes.map((node) => ({
    name: node.name,
    id: node.id,
    symbolSize: 50 // Adjust the size of the nodes
  }));

  // Convert the links into the format required by ECharts
  const formattedLinks = links.map((link) => ({
    source: link.source,
    target: link.target,
    label: {
      show: true,
      formatter: link.relationship,
    }
  }));

  // ECharts options configuration
  const getOption = () => {
    return {
      tooltip: {},
      series: [{
        type: 'graph',
        layout: 'force',
        data: formattedNodes,
        links: formattedLinks,
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
