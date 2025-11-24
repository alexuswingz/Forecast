"""
Forecast Visualization - Generate interactive charts
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ForecastVisualizer:
    """Create visualizations for forecast data"""
    
    def __init__(self, historical_df: pd.DataFrame,
                 forecast_df: pd.DataFrame,
                 inventory_plan: dict,
                 product_info: dict):
        """
        Initialize visualizer
        
        Args:
            historical_df: Historical data with smoothing
            forecast_df: Future forecast data
            inventory_plan: Inventory planning metrics
            product_info: Product information
        """
        self.historical_df = historical_df
        self.forecast_df = forecast_df
        self.inventory_plan = inventory_plan
        self.product_info = product_info
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        
    def plot_sales_forecast(self, figsize=(16, 8)) -> plt.Figure:
        """
        Plot historical sales and future forecast
        
        Shows:
        - Actual units sold (historical)
        - Smoothed historical data
        - Forecast with seasonality
        - Combined view matching Excel format
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        hist = self.historical_df
        forecast = self.forecast_df
        
        # Plot 1: Historical actual sales (blue line with dots)
        ax.plot(hist['week_end'], hist['units_sold'],
                label='units_sold', color='#4472C4', linewidth=2, marker='o', markersize=3)
        
        # Plot 2: Historical smoothed (red line)
        ax.plot(hist['week_end'], hist['units_final_smooth'],
                label='units_final_smooth', color='#ED7D31', linewidth=2.5)
        
        # Plot 3: Forecast adjusted (orange line) - continuing from historical
        ax.plot(forecast['week_end'], forecast['forecast_adjusted'],
                label='adj_forecast', color='#FFC000', linewidth=2.5)
        
        # Plot 4: Forecast smoothed continuation (green line)
        # Apply smoothing to the forecast for visual continuity
        forecast_smooth = forecast['forecast_adjusted'].rolling(window=3, min_periods=1).mean()
        ax.plot(forecast['week_end'], forecast_smooth,
                label='forecast_final_smooth', color='#70AD47', linewidth=2.5)
        
        # Add vertical line at forecast start (subtle)
        if len(hist) > 0:
            forecast_start = hist['week_end'].max()
            ax.axvline(forecast_start, color='gray', linestyle='--', alpha=0.3, linewidth=1)
        
        # Formatting to match Excel style
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Units', fontsize=11)
        
        title = f"Sales Forecast: {self.product_info.get('title', 'Unknown')[:50]}"
        ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
        
        # Legend at top
        ax.legend(loc='upper left', frameon=True, ncol=4, fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Format x-axis to show dates nicely
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
        
        # Set y-axis to start at 0
        ax.set_ylim(bottom=0)
        
        plt.tight_layout()
        
        return fig
    
    def plot_smoothing_detail(self, figsize=(16, 10)) -> plt.Figure:
        """
        Plot detailed smoothing components
        
        Shows:
        - Raw data
        - Peak envelope
        - Smooth envelope
        - Final curve
        - Final smooth
        """
        hist = self.historical_df
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        
        # Sales smoothing
        ax1.plot(hist['week_end'], hist['units_sold'],
                label='Raw Sales', color='#2E86AB', linewidth=1.5, marker='o', markersize=3, alpha=0.6)
        ax1.plot(hist['week_end'], hist['units_peak_env'],
                label='Peak Envelope', color='#A23B72', linewidth=2, linestyle='--')
        ax1.plot(hist['week_end'], hist['units_smooth_env'],
                label='Smooth Envelope', color='#F18F01', linewidth=2, linestyle=':')
        ax1.plot(hist['week_end'], hist['units_final_smooth'],
                label='Final Smooth', color='#C73E1D', linewidth=2.5)
        
        ax1.set_xlabel('Week Ending', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Units', fontsize=11, fontweight='bold')
        ax1.set_title('Sales Smoothing Components', fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='best', frameon=True, shadow=True)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Search volume smoothing
        ax2.plot(hist['week_end'], hist['search_volume'],
                label='Raw Search Volume', color='#2E86AB', linewidth=1.5, marker='o', markersize=3, alpha=0.6)
        ax2.plot(hist['week_end'], hist['sv_peak_env'],
                label='Peak Envelope', color='#A23B72', linewidth=2, linestyle='--')
        ax2.plot(hist['week_end'], hist['sv_smooth_env'],
                label='Smooth Envelope', color='#F18F01', linewidth=2, linestyle=':')
        ax2.plot(hist['week_end'], hist['sv_final_smooth'],
                label='Final Smooth', color='#C73E1D', linewidth=2.5)
        
        ax2.set_xlabel('Week Ending', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Search Volume', fontsize=11, fontweight='bold')
        ax2.set_title('Search Volume Smoothing Components', fontsize=13, fontweight='bold', pad=15)
        ax2.legend(loc='best', frameon=True, shadow=True)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        return fig
    
    def plot_inventory_plan(self, figsize=(16, 8)) -> plt.Figure:
        """
        Plot inventory planning visualization
        
        Shows:
        - Cumulative forecast
        - Current inventory levels
        - Runout dates
        - DOI goals
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        
        # Calculate cumulative forecast
        forecast = self.forecast_df.copy()
        forecast['cumulative_forecast'] = forecast['forecast_adjusted'].cumsum()
        
        # Current inventory
        total_inv = self.inventory_plan['current_inventory']
        available_fba = self.inventory_plan['inventory_breakdown'].get('available_fba', 0)
        
        # Plot 1: Cumulative forecast vs inventory
        ax1.plot(forecast['week_end'], forecast['cumulative_forecast'],
                label='Cumulative Forecast', color='#2E86AB', linewidth=2.5)
        
        # Add horizontal lines for inventory levels
        ax1.axhline(total_inv, color='#A23B72', linestyle='--', linewidth=2,
                   label=f'Total Inventory ({total_inv:,.0f} units)')
        ax1.axhline(available_fba, color='#F18F01', linestyle='--', linewidth=2,
                   label=f'Available FBA ({available_fba:,.0f} units)')
        
        # Add runout date markers
        runout_total = self.inventory_plan['runout_date_total']
        runout_fba = self.inventory_plan['runout_date_fba_available']
        
        ax1.axvline(pd.Timestamp(runout_total), color='#A23B72', linestyle=':', alpha=0.7,
                   label=f'Total Runout ({runout_total.strftime("%Y-%m-%d")})')
        ax1.axvline(pd.Timestamp(runout_fba), color='#F18F01', linestyle=':', alpha=0.7,
                   label=f'FBA Runout ({runout_fba.strftime("%Y-%m-%d")})')
        
        ax1.set_xlabel('Week Ending', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Cumulative Units', fontsize=11, fontweight='bold')
        ax1.set_title('Inventory Runout Forecast', fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='best', frameon=True, shadow=True, fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Plot 2: Weekly forecast
        ax2.bar(forecast['week_end'], forecast['forecast_adjusted'],
               width=6, color='#2E86AB', alpha=0.7, label='Weekly Forecast')
        
        # Add average line
        avg_forecast = forecast['forecast_adjusted'].mean()
        ax2.axhline(avg_forecast, color='#C73E1D', linestyle='--', linewidth=2,
                   label=f'Average ({avg_forecast:.0f} units/week)')
        
        ax2.set_xlabel('Week Ending', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Units per Week', fontsize=11, fontweight='bold')
        ax2.set_title('Weekly Forecast Breakdown', fontsize=13, fontweight='bold', pad=15)
        ax2.legend(loc='best', frameon=True, shadow=True)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        return fig
    
    def plot_inventory_breakdown(self, figsize=(10, 6)) -> plt.Figure:
        """
        Plot inventory breakdown pie chart
        """
        breakdown = self.inventory_plan['inventory_breakdown']
        
        # Prepare data
        labels = []
        sizes = []
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        
        for key, value in breakdown.items():
            if key != 'latest_date' and value > 0:
                labels.append(key.replace('_', ' ').title())
                sizes.append(value)
        
        if len(sizes) == 0:
            print("  No inventory data to plot")
            return None
        
        fig, ax = plt.subplots(figsize=figsize)
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors[:len(sizes)],
                                           autopct='%1.1f%%', startangle=90,
                                           textprops={'fontsize': 11, 'weight': 'bold'})
        
        # Make percentage text more visible
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
        
        ax.set_title(f'Current Inventory Breakdown\nTotal: {self.inventory_plan["current_inventory"]:,.0f} units',
                    fontsize=13, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        return fig
    
    def generate_all_charts(self, export_path: Optional[str] = None) -> dict:
        """
        Generate all charts and save to files
        
        Returns:
            dict mapping chart names to figure objects
        """
        charts = {}
        
        print("\n" + "=" * 70)
        print(" GENERATING VISUALIZATIONS")
        print("=" * 70)
        
        # Generate charts
        print("\n1. Sales Forecast Chart...")
        charts['sales_forecast'] = self.plot_sales_forecast()
        
        print("2. Smoothing Detail Chart...")
        charts['smoothing_detail'] = self.plot_smoothing_detail()
        
        print("3. Inventory Plan Chart...")
        charts['inventory_plan'] = self.plot_inventory_plan()
        
        print("4. Inventory Breakdown Chart...")
        charts['inventory_breakdown'] = self.plot_inventory_breakdown()
        
        # Save charts
        if export_path:
            Path(export_path).mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            asin = self.product_info.get('asin', 'unknown')
            
            print("\n Saving charts...")
            for name, fig in charts.items():
                if fig is not None:
                    filepath = f"{export_path}/{name}_{asin}_{timestamp}.png"
                    fig.savefig(filepath, dpi=150, bbox_inches='tight')
                    print(f"    {filepath}")
            
            print("\n All charts saved!")
        
        return charts
    
    def show(self):
        """Display all charts"""
        plt.show()


def visualize_forecast(asin: Optional[str] = None, sku: Optional[str] = None,
                      start_date: Optional[str] = None,
                      export_path: str = 'forecasting/output',
                      show_charts: bool = True):
    """
    Generate and visualize forecast for a product
    
    Args:
        asin: Product ASIN
        sku: Product SKU
        start_date: Start date for historical data
        export_path: Path to save charts
        show_charts: Whether to display charts interactively
    """
    from forecasting.generate_forecast import ForecastGenerator
    
    # Generate forecast
    generator = ForecastGenerator(asin=asin, sku=sku)
    hist_df, forecast_df, inv_plan = generator.generate(
        start_date=start_date,
        export_csv=True,
        export_path=export_path
    )
    
    # Create visualizations
    visualizer = ForecastVisualizer(
        historical_df=hist_df,
        forecast_df=forecast_df,
        inventory_plan=inv_plan,
        product_info=generator.product_info
    )
    
    # Generate and save charts
    charts = visualizer.generate_all_charts(export_path=export_path)
    
    # Show charts if requested
    if show_charts:
        print("\n Displaying charts (close windows to exit)...")
        visualizer.show()
    
    return visualizer, charts


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize product forecast')
    parser.add_argument('--asin', type=str, help='Product ASIN to forecast')
    parser.add_argument('--sku', type=str, help='Product SKU to forecast')
    parser.add_argument('--start-date', type=str, help='Start date for historical data (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='forecasting/output', help='Output directory for charts')
    parser.add_argument('--no-show', action='store_true', help='Do not display charts')
    
    args = parser.parse_args()
    
    if not args.asin and not args.sku:
        print(" Error: Must provide either --asin or --sku")
        return
    
    # Generate and visualize forecast
    visualize_forecast(
        asin=args.asin,
        sku=args.sku,
        start_date=args.start_date,
        export_path=args.output,
        show_charts=not args.no_show
    )


if __name__ == '__main__':
    main()

