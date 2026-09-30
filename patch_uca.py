import re
import sys
from pathlib import Path

# --- NEW PATCH: Fix Thunar 4.21 Toolbar Assertion Typo ---
print("--> Scanning for Thunar UCA toolbar assertion bug...")
for c_file in Path(".").rglob("*.c"):
    content = c_file.read_text()
    if "thunar_get_unqiue_id_from_uca_action_id" in content:
        lines = content.split('\n')
        patched_this_file = False
        for i, line in enumerate(lines):
            if "thunar_get_unqiue_id_from_uca_action_id" in line:
                # Look ahead up to 15 lines inside the function for the inverted assertion
                for j in range(i, min(i + 15, len(lines))):
                    if "!thunar_is_uca_action_id" in lines[j]:
                        lines[j] = lines[j].replace("!thunar_is_uca_action_id",
                                                    "thunar_is_uca_action_id")
                        print(
                            f"--> Successfully patched GTK assertion typo in: {c_file} (line {j+1})"
                        )
                        patched_this_file = True
        if patched_this_file:
            c_file.write_text('\n'.join(lines))

# --- EXISTING PATCH: GVFS admin:// URI resolution ---
uca_files = [p for p in Path(".").rglob("*.c") if "thunar-uca" in str(p)]
if not uca_files:
    print("Error: No thunar-uca C files found!")
    sys.exit(1)

helper_code = """
static gchar *
thunar_uca_get_path_for_file (GFile *location)
{
  gchar *path;
  if (location == NULL)
    return NULL;
  path = g_file_get_path (location);
  if (path == NULL && g_file_has_uri_scheme (location, "admin"))
    {
      gchar *uri = g_file_get_uri (location);
      if (uri != NULL)
        {
          if (g_str_has_prefix (uri, "admin://localhost"))
            path = g_strdup (uri + 17);
          else if (g_str_has_prefix (uri, "admin://"))
            path = g_strdup (uri + 8);
          else
            path = g_strdup (uri);
          if (path != NULL && path[0] == '\\0')
            {
              g_free (path);
              path = g_strdup ("/");
            }
          g_free (uri);
        }
    }
  return path;
}
"""

patched = False
for c_file in uca_files:
    content = c_file.read_text()
    if "g_file_get_path" in content:
        content = re.sub(r'\bg_file_get_path\b',
                         'thunar_uca_get_path_for_file', content)
        includes_end = content.rfind("#include")
        if includes_end != -1:
            line_end = content.find("\n", includes_end)
            content = content[:line_end +
                              1] + "\n" + helper_code + "\n" + content[
                                  line_end + 1:]
        else:
            content = helper_code + "\n" + content
        c_file.write_text(content)
        print(f"--> Successfully patched path resolution in: {c_file}")
        patched = True

if patched:
    print("--> All UCA source patches applied successfully!")
else:
    print("--> Error: No g_file_get_path calls found in UCA sources.")
    sys.exit(1)

# --- NEW PATCH: Close Other Tabs action (<Primary><Alt>w) ---
print("--> Scanning for thunar-window.h and thunar-window.c to add Close Other Tabs...")
window_h_files = [p for p in Path(".").rglob("thunar-window.h")]
window_c_files = [p for p in Path(".").rglob("thunar-window.c")]

if not window_h_files or not window_c_files:
    print("Error: Could not find thunar-window.h or thunar-window.c")
    sys.exit(1)

window_h = window_h_files[0]
content_h = window_h.read_text()
if "THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS" not in content_h:
    target_h = "  THUNAR_WINDOW_ACTION_CLOSE_TAB,\n"
    replacement_h = "  THUNAR_WINDOW_ACTION_CLOSE_TAB,\n  THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS,\n"
    if target_h in content_h:
        content_h = content_h.replace(target_h, replacement_h, 1)
        window_h.write_text(content_h)
        print(f"--> Added THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS to: {window_h}")
    else:
        print("Error: Could not find THUNAR_WINDOW_ACTION_CLOSE_TAB in thunar-window.h")
        sys.exit(1)

window_c = window_c_files[0]
content_c = window_c.read_text()
if "thunar_window_action_close_other_tabs" not in content_c:
    # 1. Forward declaration
    target_decl = "static gboolean\nthunar_window_action_close_tab (ThunarWindow *window,\n                                GtkWidget    *menu_item);\n"
    replacement_decl = target_decl + "static gboolean\nthunar_window_action_close_other_tabs (ThunarWindow *window,\n                                      GtkWidget    *menu_item);\n"
    if target_decl in content_c:
        content_c = content_c.replace(target_decl, replacement_decl, 1)
    else:
        print("Error: Could not find thunar_window_action_close_tab declaration in thunar-window.c")
        sys.exit(1)

    # 2. Action entry
    target_entry = '    { THUNAR_WINDOW_ACTION_CLOSE_TAB,                      "<Actions>/ThunarWindow/close-tab",                       "<Primary>w",           XFCE_GTK_IMAGE_MENU_ITEM, N_ ("Close Ta_b"),             N_ ("Close this folder"),                                                            "window-close",            G_CALLBACK (thunar_window_action_close_tab),          },\n'
    new_entry = '    { THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS,                "<Actions>/ThunarWindow/close-other-tabs",                 "<Primary><Alt>w",    XFCE_GTK_IMAGE_MENU_ITEM, N_ ("Close Other T_abs"),      N_ ("Close all other tabs in this window"),                                          "tab-close-other",         G_CALLBACK (thunar_window_action_close_other_tabs),    },\n'
    if target_entry in content_c:
        content_c = content_c.replace(target_entry, target_entry + new_entry, 1)
    else:
        print("Error: Could not find action entry for CLOSE_TAB in thunar-window.c")
        sys.exit(1)

    # 3. File menu
    target_filemenu = "  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_TAB), G_OBJECT (window), GTK_MENU_SHELL (menu));\n  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_WINDOW), G_OBJECT (window), GTK_MENU_SHELL (menu));\n"
    replacement_filemenu = """  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_TAB), G_OBJECT (window), GTK_MENU_SHELL (menu));
  item = xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS), G_OBJECT (window), GTK_MENU_SHELL (menu));
  gtk_widget_set_sensitive (item, gtk_notebook_get_n_pages (GTK_NOTEBOOK (window->notebook_selected)) > 1);
  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_WINDOW), G_OBJECT (window), GTK_MENU_SHELL (menu));
"""
    if target_filemenu in content_c:
        content_c = content_c.replace(target_filemenu, replacement_filemenu, 1)
    else:
        print("Error: Could not find file menu target in thunar-window.c")
        sys.exit(1)

    # 4. Notebook popup menu (declare item variable at top of function)
    target_popup_func = "thunar_window_notebook_popup_menu (GtkWidget    *notebook,\n                                   ThunarWindow *window)\n{\n  GtkWidget *menu;\n"
    replacement_popup_func = "thunar_window_notebook_popup_menu (GtkWidget    *notebook,\n                                   ThunarWindow *window)\n{\n  GtkWidget *menu;\n  GtkWidget *item;\n"
    if target_popup_func in content_c:
        content_c = content_c.replace(target_popup_func, replacement_popup_func, 1)
    else:
        print("Error: Could not find thunar_window_notebook_popup_menu declaration in thunar-window.c")
        sys.exit(1)

    target_popup = "  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_TAB), G_OBJECT (window), GTK_MENU_SHELL (menu));\n  gtk_widget_show_all (menu);\n"
    replacement_popup = """  xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_TAB), G_OBJECT (window), GTK_MENU_SHELL (menu));
  item = xfce_gtk_menu_item_new_from_action_entry (get_action_entry (THUNAR_WINDOW_ACTION_CLOSE_OTHER_TABS), G_OBJECT (window), GTK_MENU_SHELL (menu));
  gtk_widget_set_sensitive (item, gtk_notebook_get_n_pages (GTK_NOTEBOOK (notebook)) > 1);
  gtk_widget_show_all (menu);
"""
    if target_popup in content_c:
        content_c = content_c.replace(target_popup, replacement_popup, 1)
    else:
        print("Error: Could not find notebook popup menu target in thunar-window.c")
        sys.exit(1)

    # 5. Implementation
    func_impl = """
static gboolean
thunar_window_action_close_other_tabs (ThunarWindow *window,
                                       GtkWidget    *menu_item)
{
  GtkNotebook *notebook;
  gint         current_page_idx;
  GtkWidget   *current_page;
  gint         n_pages;
  gint         i;

  _thunar_return_val_if_fail (THUNAR_IS_WINDOW (window), FALSE);

  notebook = GTK_NOTEBOOK (window->notebook_selected);
  if (notebook == NULL)
    return TRUE;

  n_pages = gtk_notebook_get_n_pages (notebook);
  if (n_pages <= 1)
    return TRUE;

  current_page_idx = gtk_notebook_get_current_page (notebook);
  current_page = gtk_notebook_get_nth_page (notebook, current_page_idx);
  if (current_page == NULL)
    return TRUE;

  for (i = n_pages - 1; i >= 0; i--)
    {
      GtkWidget *page = gtk_notebook_get_nth_page (notebook, i);
      if (page != NULL && page != current_page)
        gtk_widget_destroy (page);
    }

  return TRUE;
}
"""
    target_close_tab = "  /* required in case of shortcut activation, in order to signal that the accel key got handled */\n  return TRUE;\n}\n\n\n\nstatic gboolean\nthunar_window_action_close_window"
    if target_close_tab in content_c:
        content_c = content_c.replace(target_close_tab, "  /* required in case of shortcut activation, in order to signal that the accel key got handled */\n  return TRUE;\n}\n" + func_impl + "\n\n\nstatic gboolean\nthunar_window_action_close_window", 1)
        window_c.write_text(content_c)
        print(f"--> Successfully patched thunar-window.c with Close Other Tabs!")
    else:
        print("Error: Could not find thunar_window_action_close_tab end in thunar-window.c")
        sys.exit(1)
