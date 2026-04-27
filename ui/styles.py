"""CSS stylesheet generation. Colour palettes live in ui.theme."""

from ui.theme import (
    item_height, font, font_size, border_radius, border,
    scroll_color, scroll_hover_color,
    palettes,
    TEXT_COLOR, TEXT_COLOR2, TEXT_BG_COLOR, BORDER_COLOR,
    HOVER_BORDER, HOVER_TAB, HOVER_TABLE, SELECTED_TAB, SELECT_COLOR,
    BORDER, BG_COLOR, BG_COLOR2, BG_COLOR3, BG_ICON_COLOR,
)

# Re-export accessor helpers so existing `from ui.styles import get_*` keeps working
from ui.theme import (  # noqa: F401
    get_border_color, get_hover_color, get_select_color,
    get_text_color, get_text_bg_color, get_bg_color,
)

def get_styles(style_name: str) -> str:
    style_data: dict = palettes[style_name]

    scroll_style: str = f"""
        QScrollArea {{ 
            background: transparent; 
            border: none;
        }}

        QScrollBar:vertical {{
            border-left: {style_data[BORDER]};
            border-right: {style_data[BORDER]};
            border-top: {style_data[BORDER]};
            background: transparent;
            width: 16px;
            padding: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {scroll_color};
            min-height: 32px;
            margin: 0px;
            margin-bottom: 3px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {scroll_hover_color};
            min-height: 32px;
            width: 16px;
            border-radius: 4px;
        }}

        QScrollBar::sub-line:vertical {{
            border: none;
            background: transparent;
            image: url("img/up.png");
            height: 20px;
            width: 20px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }}

        QScrollBar::add-line:vertical {{
            border: none;
            background: transparent;
            image: url("img/down.png");
            height: 20px;
            width: 20px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }}

        QScrollBar::sub-page:vertical,
        QScrollBar::add-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            border: none;
            background: {style_data[BG_COLOR]};
            height: 16px;
            margin: 0px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {scroll_color};
            min-width: 30px;
            border-radius: 6px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {scroll_hover_color};
        }}
        QScrollBar::sub-line:horizontal,
        QScrollBar::add-line:horizontal {{
            border: none;
            background: none;
            width: 0px;
        }}
        QScrollBar::sub-page:horizontal,
        QScrollBar::add-page:horizontal {{
            background: none;
        }}
    """

    tree_style: str = f"""
        QTreeWidget {{
            background: transparent;
            font-family: {font};
            color: {style_data[TEXT_COLOR]};
            font-weight: 500;
            font-size: {font_size};
            border: {style_data[BORDER]};
            border-radius: {border_radius};
            outline: 0;
        }}

        QTreeWidget::item {{
            background: transparent;
            border-bottom: {style_data[BORDER]};
            border-right: {style_data[BORDER]};
            padding: 0px;
            margin: 0px;
            min-height: {item_height}px;
        }}

        QTreeWidget::item:hover {{
            background: {style_data[HOVER_TABLE]};
        }}

        QTreeWidget::item:selected {{
            background: {style_data[SELECT_COLOR]};
        }}

        QTreeWidget::item:selected:active {{
            background: {style_data[SELECT_COLOR]};
        }}

        QTreeWidget::item:selected:!active {{
            background: {style_data[SELECT_COLOR]};
        }}

        QTreeWidget::branch {{
            background: transparent;
        }}

        QHeaderView {{
            background: transparent;
        }}

        QHeaderView::section {{
            background: transparent;
            font-family: {font};
            font-weight: 600;
            color: {style_data[TEXT_COLOR]};
            font-size: {font_size};
            border: {style_data[BORDER]};
            padding: 4px 2px;
        }}

        QHeaderView::section:last {{
            background: transparent;
            border-top-right-radius: 10px;
        }}

        QHeaderView::section:first {{
            background: transparent;
            border-top-left-radius: 10px;
        }}

        QTreeWidget::indicator {{
            width: 0px;
            height: 0px;
        }}
    """

    tab_style: str = f"""
        QTabWidget#tab_widget::pane {{
            border: none;
            padding: 5px;
            margin: 0px;
            background: {style_data[BG_COLOR2]};
        }}
        QTabWidget#tab_widget QTabBar {{
            background: {style_data[BG_COLOR]};
            margin-top: 5px;
        }}
        QTabWidget#tab_widget QTabBar::tab {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            padding: 8px 20px;
            outline: none;
            margin: 0px;
            margin-left: 10px;
            border: none;
            font-size: {font_size};
            font-weight: 500;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
        QTabWidget#tab_widget QTabBar::tab:hover {{
            background: {style_data[HOVER_TAB]};
        }}
        QTabWidget#tab_widget QTabBar::tab:selected {{
            background: {style_data[BG_COLOR2]};
            outline: none;
            color: {style_data[TEXT_COLOR]};
            font-weight: 500;
            border: none;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
    """

    btn_style: str = f"""
        QPushButton#status_btn {{
            background: transparent;
            border-radius: 8px;
            padding: 4px;
            outline: none;
            border: none;
        }}
        QPushButton#status_btn:hover {{
            background: {style_data[BG_COLOR2]};
        }}
        
        QPushButton#top_btn {{
            background: transparent;
            font-size: 32px;
            color: {style_data[TEXT_COLOR]};
            border-radius: 5px;
            padding: 3px;
            outline: none;
        }}
        QPushButton#top_btn:hover {{
            background: {style_data[BG_COLOR3]};
        }}
        
        QPushButton#exit_btn {{
            background: transparent;
            font-size: 32px;
            color: {style_data[TEXT_COLOR]};
            border-radius: 5px;
            padding-bottom: 8px;
            text-align: center;
            margin-right: 10px;
            outline: none;
        }}
        QPushButton#exit_btn:hover {{
            background: #f44;
        }}
        
        QPushButton#save_btn {{
            background-color: #007CF0;
            border-radius: 12px;
            color: #FFF;
            padding: 12px 20px;
            font-size: 16px;
            font-family: {font};
            font-weight: 500;
            outline: none;
            border: none;
        }}
        
        QPushButton#auto {{
            background: {style_data[BG_COLOR2]};
            border-radius: 8px;
            outline: none;
            border: none;
            padding: 10px 14px;
            font-size: 14px;
            font-family: {font};
            font-weight: 500;
            color: {style_data[TEXT_COLOR]};
        }}
        QPushButton#auto:hover {{
            border: 1px solid {style_data[HOVER_BORDER]};
        }}
        
        QPushButton#image_btn {{
            background: {style_data[BG_COLOR2]};
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            font-family: {font};
            color: {style_data[TEXT_COLOR]};
            border: {border};
            padding: 5px;
        }}
        QPushButton#image_btn:hover {{
            background: {style_data[HOVER_TABLE]};
        }}
        
        QPushButton#item_image {{
            background: transparent;
            padding: 5px 15px;
            font-size: {font_size};
            font-family: {font};
            border: none;
            outline: none;
        }}
    
        QPushButton#item_id_image {{
            background: transparent;
            padding: 5px 30px;
            padding-left: 30px;
            font-size: {font_size};
            font-family: {font};
            border: none;
            outline: none;
        }}
    
        QPushButton#save_btn:hover {{
            border: 1px solid {style_data[HOVER_BORDER]};
        }}
    
        QPushButton#back_btn {{
            background: {style_data[BG_COLOR2]};
            border-radius: 12px;
            color: {style_data[TEXT_COLOR2]};
            padding: 12px 20px;
            font-size: 16px;
            font-family: {font};
            font-weight: 500;
            outline: none;
            border: {style_data[BORDER]};
        }}
    
        QPushButton#back_btn:hover {{
            border: 1px solid {style_data[HOVER_BORDER]};
        }}
    
        QPushButton#save_btn:disabled {{
            background-color: #ccc;
            color: #f00;
        }}
    
        QPushButton#toggle_btn {{
            background: transparent;
            outline: none;
            border: none;
            padding: 0px;
            margin: 0px;
        }}
    """

    edit_style: str = f"""
        QLineEdit#hidden_settings_edit {{
            background: transparent;
            border: none;
            padding-bottom: 5px;
            color: {style_data[TEXT_COLOR]};
            font-size: 16px;
            font-weight: 500;
            font-family: {font};
        }}
        QLineEdit#hidden_settings_edit:focus {{
            border-bottom: {style_data[BORDER]};
        }}
        QLineEdit#hidden_settings_edit:hover {{
            border-bottom: {style_data[BORDER]};
        }}
        QLineEdit#hidden_settings_edit:focusout {{
            border: none;
        }}
    
        QLineEdit#hidden1_settings_edit {{
            background: transparent;
            border: none;
            border-bottom: {style_data[BORDER]};
            padding-bottom: 5px;
            color: {style_data[TEXT_COLOR2]};
            font-size: 14px;
            font-weight: 500;
            font-family: {font};
        }}
        QLineEdit#wrong_password {{
            background: transparent;
            border: none;
            border-bottom: 2px solid #f00;
            padding-bottom: 5px;
            color: {style_data[TEXT_COLOR2]};
            font-size: 14px;
            font-weight: 500;
            font-family: {font};
        }}
        
        QLineEdit#theme_edit {{
            background-color: transparent;
            border: none;
            color: {style_data[TEXT_COLOR]};
            font-size: 14px;
            font-weight: 500;
            font-family: {font};
        }}
    
        QLineEdit#settings_edit {{
            background: transparent;
            border: none;
            padding-bottom: 5px;
            border-bottom: {style_data[BORDER]};
            color: {style_data[TEXT_COLOR]};
            font-size: 14px;
            font-weight: 500;
            font-family: {font};
        }}
    """

    widget_style: str = f"""
        QMainWindow {{
            background: {style_data[BG_COLOR]};
        }}
        QDialog {{
            background: {style_data[BG_COLOR2]};
        }}
        QDialog#hidden_settings {{
            background: {style_data[BG_COLOR2]};
        }}
        QDialog#modal {{
            background: {style_data[BG_COLOR2]};
        }}
        QWidget#cam_widget {{
            background: {style_data[BG_COLOR2]};
        }}
        QWidget#horizontal_widget {{
            background: {style_data[BG_COLOR2]};
            border: {style_data[BORDER]};
            border-radius: 20px;
        }}
        
        QWidget#title_widget {{
            background: transparent;
            border-bottom: {style_data[BORDER]};
        }}
    
        QWidget#side_widget {{
            background: {style_data[BG_COLOR2]};
            border-radius: 30px;
            padding: 5px 10px;
            border: {style_data[BORDER]};
        }}
        QWidget#history_widget {{
            background: {style_data[BG_COLOR]};
        }}
        QWidget#status_widget {{
            background: {style_data[BG_COLOR]};
            padding: 0px;
            margin: 0px;
        }}
        
        QWidget#item_row {{
            background: transparent;
            border-bottom: {style_data[BORDER]};
        }}
        QWidget#item_row:hover {{
            background: {style_data[HOVER_TAB]};
        }}
    
        QWidget#central {{
            background: transparent;
            border: {style_data[BORDER]};
        }}
        QWidget#settings_widget {{
            background: {style_data[BG_COLOR]};
            border: {style_data[BORDER]};
        }}
    """

    check_style: str = f"""
        QCheckBox {{
            background: transparent;
            margin-right: 10px;
        }}
        QCheckBox:disabled {{
            background: transparent;
        }}
    """

    lbl_style: str = f"""
        QLabel#frame_lbl {{
            background: {style_data[BG_COLOR]};
            border-radius: 24px;
        }}
        
        QLabel#icon_lbl {{
            background: transparent;
            margin: 5px;
            margin-left: 10px;
        }}
        
        QLabel#title_lbl {{
            background: transparent;
            font-family: {font};
            font-weight: 600;
            font-size: 28px;
            margin-left: 4px;
            color: {style_data[TEXT_COLOR]};
            border: none;
        }}
    
        QLabel#archive {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border: 3px solid #007CF0;
            border-radius: 14px;
            font-size: 13px;
            font-weight: 700;
            font-family: {font};
            margin: 1px 15px;
        }}
        
        QLabel#right_lbl {{
            background: transparent;
            color: #007CF0;
            font-size: 24px;
            font-weight: 500;
            font-family: {font};
            margin-right: 13px;
        }}
        
    
        QLabel#center_lbl {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            font-family: {font};
            font-weight: 700;
            font-size: 16px;
        }}
    
        QLabel#left_icon_lbl {{
            background: {style_data[BG_ICON_COLOR]};
            padding: 13px;
            margin-left: 12px;
            border-radius: 12px;
            border: none;
        }}
    
        QLabel#toggle_lbl {{
            background: transparent;
            padding-right: 15px;
            padding-top: 16px;
            font-size: {font_size};
            color: {style_data[TEXT_COLOR]};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#side_lbl {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            padding: 3px;
            font-size: 20px;
            font-weight: 600;
            font-family: {font};
        }}
    
        QLabel#state_lbl {{
            background: transparent;
            color: {style_data[TEXT_COLOR2]};
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#number_text {{
            background-color: transparent;
            font-size: {font_size};
            color: #fff;
            padding-left: 10px;
            font-weight: 700;
            font-family: {font};
        }}
        QLabel#number {{
            background-color: rgba(255, 255, 255, 30);
            padding: 9px 30px;
            margin: 0px 16px;
            color: #fff;
            border-radius: 8px;
            font-size: 24px;
            font-weight: 500;
            font-family: {font};
        }}
        QLabel#number_image {{
            background-color: rgba(255, 255, 255, 30);
            padding: 0px;
            color: #fff;
            border-radius: 8px;
            font-family: {font};
        }}
        QLabel#settings {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            font-size: 32px;
            font-family: {font};
            font-weight: 600;
        }}
        QLabel#settings_lbl {{
            background-color: transparent;
            color: {style_data[TEXT_COLOR2]};
            font-size: 15px;
            font-family: {font};
            font-weight: 500;
        }}
        
        QLabel#header_l {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border-top-left-radius: 20px;
            border-left: {style_data[BORDER]};
            border-top: {style_data[BORDER]};
            border-bottom: {style_data[BORDER]};
            padding-left: 15px;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
        QLabel#header_r {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border-top-right-radius: 20px;
            border-right: {style_data[BORDER]};
            border-top: {style_data[BORDER]};
            border-bottom: {style_data[BORDER]};
            font-size: {font_size};
            padding-left: 15px;
            font-weight: 500;
            font-family: {font};
        }}
        QLabel#header_id {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border-top: {style_data[BORDER]};
            border-bottom: {style_data[BORDER]};
            font-size: {font_size};
            padding-left: 30px;
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#header {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border-top: {style_data[BORDER]};
            border-bottom: {style_data[BORDER]};
            font-size: {font_size};
            padding-left: 15px;
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_l {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            font-size: {font_size};
            padding-left: 15px;
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_id {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            padding-left: 30px;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            padding-left: 15px;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_massa_green {{
            background: transparent;
            color: #00C954;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_kg_green {{
            background: transparent;
            color: #66DF98;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_massa_red {{
            background: transparent;
            color: #F00044;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_kg_red {{
            background: transparent;;
            color: #F6668F;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_massa_yel {{
            background: transparent;
            color: #C0A300;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#item_kg_yel {{
            background: transparent;
            color: #F0CC00;
            font-size: {font_size};
            font-weight: 500;
            font-family: {font};
        }}
    
        QLabel#theme_lbl {{
            background-color: transparent;
            color: {style_data[TEXT_COLOR2]};
            font-size: {font_size};
            font-family: {font};
            font-weight: 700;
        }}
        QLabel#settings_edit_lbl {{
            background: {style_data[BG_COLOR]};
            color: {style_data[TEXT_COLOR]};
            border-radius: 12px;
        }}
        QLabel#hidden_settings_edit_lbl {{
            background: {style_data[BG_COLOR]};
            color: {style_data[TEXT_COLOR]};
            border-radius: 12px;
            border: none;
        }}
        QLabel#hidden_settings2_edit_lbl {{
            background: transparent;
            color: {style_data[TEXT_COLOR]};
            border-radius: 12px;
            border: none;
        }}
    
        QLabel#hidden_help_settings_lbl {{
            background: transparent;
            border: none;
            padding-top: 5px;
            padding-left: 5px;
            color: {style_data[TEXT_COLOR2]};
            font-size: 12px;
            font-family: {font};
            font-weight: 500;
        }}
    
        QLabel#hidden_settings_lbl {{
            background: transparent;
            border: none;
            color: {style_data[TEXT_COLOR2]};
            font-size: 12px;
            font-family: {font};
            font-weight: 500;
        }}
    
        QLabel#hidden1_settings_lbl {{
            background: transparent;
            border: none;
            color: {style_data[TEXT_COLOR2]};
            margin-bottom: 5px;
            font-size: 16px;
            font-family: {font};
            font-weight: 700;
        }}
    """

    all_styles: str = (
            lbl_style + check_style + btn_style + edit_style +
            widget_style + tab_style + scroll_style + tree_style + scroll_style
    )
    return all_styles



# Accessor helpers are now in ui.theme and re-exported above.

