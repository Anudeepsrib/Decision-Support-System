# ARR Truing-Up DSS - Demo Data

This folder contains sample files designed to demonstrate the core features of the ARR Truing-Up Decision Support System.

## Files Included

1. **`1_True_Up_Petition_SBU_D_FY25.pdf`**
   * **Purpose**: Simulates a standard Truing-Up Petition submitted by SBU-D (Distribution).
   * **Demo Action**: Upload this file in the **PDF Uploader** tab. 
   * **Expected Feature**: Demonstrates the AI's ability to extract specific declared values (e.g., "Rs. 180.00 Cr" for O&M Cost) and map them to the standard KSERC chart of accounts.

2. **`2_Audited_Financials_SBU_G_FY25.pdf`**
   * **Purpose**: Simulates the Statutory Audit Report for SBU-G (Generation).
   * **Demo Action**: Upload this file to demonstrate cross-validation.
   * **Expected Feature**: Demonstrates how the system extracts actual audited figures (e.g., Power Purchase Cost: Rs. 850.00 Cr) to compare against the petition claims in the mapping workbench.

3. **`3_Transmission_Loss_Report_FY25.pdf`**
   * **Purpose**: Simulates a compliance report for SBU-T (Transmission).
   * **Demo Action**: Use this data to test the **Efficiency Analysis** module.
   * **Expected Feature**: Demonstrates the automated calculation of T&D line loss penalties based on the 12.20% actual vs 11.50% normative target.

## How to run the full demo:
1. Login as `regulatory.officer@kserc.gov.in` (Password: `TempPass123!`).
2. Navigate to **Upload Document** and drag-and-drop these PDFs.
3. Review the AI's extraction results in the **Mapping Workbench**.
4. Navigate to **Reports** to generate the final analytical output for FY 2024-25.
