#!/usr/bin/env python3
"""Generate the Thunar shortcut-order patch from the pristine 4.18.8 tag.

This bootstrapper keeps the upstream source tree on the disposable CI runner.
The generated unified diff is both applied to Ubuntu's source package and
published as a build artifact. Once validated, the generated diff can replace
this script as the repository's canonical patch.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import textwrap


UPSTREAM_URL = "https://gitlab.xfce.org/xfce/thunar.git"
UPSTREAM_TAG = "thunar-4.18.8"


def run(*args: str, cwd: pathlib.Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    contents = path.read_text()
    occurrences = contents.count(old)
    if occurrences != 1:
        raise RuntimeError(
            f"expected one occurrence in {path}, found {occurrences}: {old[:80]!r}"
        )
    path.write_text(contents.replace(old, new, 1))


def insert_before(path: pathlib.Path, marker: str, addition: str) -> None:
    replace_once(path, marker, addition + marker)


def replace_function(
    path: pathlib.Path, start_marker: str, end_marker: str, replacement: str
) -> None:
    contents = path.read_text()
    start = contents.index(start_marker)
    end = contents.index(end_marker, start)
    path.write_text(contents[:start] + replacement + "\n\n\n" + contents[end:])


def patch_preferences(source: pathlib.Path) -> None:
    path = source / "thunar" / "thunar-preferences.c"

    replace_once(
        path,
        """  PROP_HIDDEN_DEVICES,
  PROP_HIDDEN_BOOKMARKS,
  PROP_LAST_RESTORE_TABS,""",
        """  PROP_HIDDEN_DEVICES,
  PROP_HIDDEN_BOOKMARKS,
  PROP_SHORTCUTS_DEVICES_ORDER,
  PROP_SHORTCUTS_PLACES_ORDER,
  PROP_LAST_RESTORE_TABS,""",
    )

    marker = """  preferences_props[PROP_HIDDEN_DEVICES] =
      g_param_spec_boxed ("hidden-devices",
                          NULL,
                          NULL,
                          G_TYPE_STRV,
                          EXO_PARAM_READWRITE);

"""
    addition = marker + """  /**
   * ThunarPreferences:shortcuts-devices-order:
   *
   * Stable identifiers specifying the user-defined order of entries in the
   * Devices section of the shortcuts pane.
   **/
  preferences_props[PROP_SHORTCUTS_DEVICES_ORDER] =
      g_param_spec_boxed ("shortcuts-devices-order",
                          NULL,
                          NULL,
                          G_TYPE_STRV,
                          EXO_PARAM_READWRITE);

  /**
   * ThunarPreferences:shortcuts-places-order:
   *
   * Stable identifiers specifying the user-defined order of entries in the
   * Places section of the shortcuts pane.
   **/
  preferences_props[PROP_SHORTCUTS_PLACES_ORDER] =
      g_param_spec_boxed ("shortcuts-places-order",
                          NULL,
                          NULL,
                          G_TYPE_STRV,
                          EXO_PARAM_READWRITE);

"""
    replace_once(path, marker, addition)


def patch_model_header(source: pathlib.Path) -> None:
    path = source / "thunar" / "thunar-shortcuts-model.h"
    replace_once(
        path,
        """gboolean               thunar_shortcuts_model_drop_possible (ThunarShortcutsModel *model,
                                                             GtkTreePath          *path);""",
        """gboolean               thunar_shortcuts_model_drop_possible (ThunarShortcutsModel *model,
                                                             GtkTreePath          *src_path,
                                                             GtkTreePath          *dst_path);""",
    )


def patch_model(source: pathlib.Path) -> None:
    path = source / "thunar" / "thunar-shortcuts-model.c"

    replace_once(
        path,
        "typedef struct _ThunarShortcut ThunarShortcut;\n",
        """typedef struct _ThunarShortcut ThunarShortcut;

typedef enum
{
  THUNAR_SHORTCUT_SECTION_NONE,
  THUNAR_SHORTCUT_SECTION_PLACES,
  THUNAR_SHORTCUT_SECTION_DEVICES,
  THUNAR_SHORTCUT_SECTION_NETWORK,
} ThunarShortcutSection;
""",
    )

    replace_once(
        path,
        """static void               thunar_shortcuts_model_header_visibility  (ThunarShortcutsModel      *model);
static void               thunar_shortcuts_model_shortcut_devices   (ThunarShortcutsModel      *model);""",
        """static void               thunar_shortcuts_model_header_visibility  (ThunarShortcutsModel      *model);
static ThunarShortcutSection thunar_shortcuts_model_get_section      (ThunarShortcutGroup        group);
static void               thunar_shortcuts_model_set_order_id        (ThunarShortcutsModel      *model,
                                                                     ThunarShortcut            *shortcut,
                                                                     const gchar               *order_id);
static void               thunar_shortcuts_model_save_order          (ThunarShortcutsModel      *model,
                                                                     ThunarShortcutSection      section);
static void               thunar_shortcuts_model_shortcut_devices   (ThunarShortcutsModel      *model);""",
    )

    replace_once(
        path,
        """  ThunarPreferences    *preferences;
  gchar               **hidden_bookmarks;
  gboolean              file_size_binary;""",
        """  ThunarPreferences    *preferences;
  gchar               **hidden_bookmarks;
  gchar               **devices_order;
  gchar               **places_order;
  gboolean              file_size_binary;""",
    )

    replace_once(
        path,
        """  gchar               *tooltip;
  gint                 sort_id;

  guint                busy : 1;""",
        """  gchar               *tooltip;
  gchar               *order_id;
  gint                 order_position;
  gint                 sort_id;

  guint                busy : 1;""",
    )

    replace_once(
        path,
        """  /* hidden bookmarks */
  model->preferences = thunar_preferences_get ();
  g_object_bind_property (model->preferences, "hidden-bookmarks",""",
        """  /* hidden bookmarks and persisted shortcuts-pane order */
  model->preferences = thunar_preferences_get ();
  g_object_get (G_OBJECT (model->preferences),
                "shortcuts-devices-order", &model->devices_order,
                "shortcuts-places-order", &model->places_order,
                NULL);
  g_object_bind_property (model->preferences, "hidden-bookmarks",""",
    )

    replace_once(
        path,
        """  /* free hidden list */
  g_strfreev (model->hidden_bookmarks);
""",
        """  /* free persisted lists */
  g_strfreev (model->hidden_bookmarks);
  g_strfreev (model->devices_order);
  g_strfreev (model->places_order);
""",
    )

    replace_function(
        path,
        "static gboolean\nthunar_shortcuts_model_row_draggable",
        "static gboolean\nthunar_shortcuts_model_drag_data_get",
        textwrap.dedent(
            """\
            static gboolean
            thunar_shortcuts_model_row_draggable (GtkTreeDragSource *source,
                                                  GtkTreePath       *path)
            {
              ThunarShortcutsModel *model = THUNAR_SHORTCUTS_MODEL (source);
              ThunarShortcut       *shortcut;
              ThunarShortcutSection section;

              _thunar_return_val_if_fail (THUNAR_IS_SHORTCUTS_MODEL (model), FALSE);
              _thunar_return_val_if_fail (gtk_tree_path_get_depth (path) > 0, FALSE);

              shortcut = g_list_nth_data (model->shortcuts, gtk_tree_path_get_indices (path)[0]);
              if (shortcut == NULL || (shortcut->group & THUNAR_SHORTCUT_GROUP_HEADER) != 0)
                return FALSE;

              section = thunar_shortcuts_model_get_section (shortcut->group);
              return section == THUNAR_SHORTCUT_SECTION_PLACES
                     || section == THUNAR_SHORTCUT_SECTION_DEVICES;
            }"""
        ),
    )

    replace_once(
        path,
        """  shortcut->gicon = g_themed_icon_new ("drive-harddisk");
  shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
  thunar_shortcuts_model_add_shortcut (model, shortcut);""",
        """  shortcut->gicon = g_themed_icon_new ("drive-harddisk");
  shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
  thunar_shortcuts_model_set_order_id (model, shortcut, "device:filesystem");
  thunar_shortcuts_model_add_shortcut (model, shortcut);""",
    )

    replace_once(
        path,
        """  g_signal_connect (model->device_monitor, "device-changed", G_CALLBACK (thunar_shortcuts_model_device_changed), model);

  thunar_shortcuts_model_header_visibility (model);""",
        """  g_signal_connect (model->device_monitor, "device-changed", G_CALLBACK (thunar_shortcuts_model_device_changed), model);

  if (model->devices_order == NULL)
    thunar_shortcuts_model_save_order (model, THUNAR_SHORTCUT_SECTION_DEVICES);

  thunar_shortcuts_model_header_visibility (model);""",
    )

    replacements = (
        (
            """      shortcut->gicon = g_themed_icon_new ("go-home");
      shortcut->sort_id = 0;
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);""",
            """      shortcut->gicon = g_themed_icon_new ("go-home");
      shortcut->sort_id = 0;
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
      thunar_shortcuts_model_set_order_id (model, shortcut, "place:home");""",
        ),
        (
            """          shortcut->file = file;
          shortcut->sort_id =  1;
          shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);""",
            """          shortcut->file = file;
          shortcut->sort_id =  1;
          shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
          thunar_shortcuts_model_set_order_id (model, shortcut, "place:desktop");""",
        ),
        (
            """          shortcut->name = g_strdup (_("Trash"));
          shortcut->file = file;
          shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);""",
            """          shortcut->name = g_strdup (_("Trash"));
          shortcut->file = file;
          shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
          thunar_shortcuts_model_set_order_id (model, shortcut, "place:trash");""",
        ),
        (
            """      shortcut->gicon = g_themed_icon_new ("computer");
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);""",
            """      shortcut->gicon = g_themed_icon_new ("computer");
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
      thunar_shortcuts_model_set_order_id (model, shortcut, "place:computer");""",
        ),
        (
            """      shortcut->gicon = g_themed_icon_new ("document-open-recent");
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);""",
            """      shortcut->gicon = g_themed_icon_new ("document-open-recent");
      shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
      thunar_shortcuts_model_set_order_id (model, shortcut, "place:recent");""",
        ),
    )
    for old, new in replacements:
        replace_once(path, old, new)

    helper_code = textwrap.dedent(
        """\
        static ThunarShortcutSection
        thunar_shortcuts_model_get_section (ThunarShortcutGroup group)
        {
          if ((group & THUNAR_SHORTCUT_GROUP_PLACES) != 0)
            return THUNAR_SHORTCUT_SECTION_PLACES;
          if ((group & THUNAR_SHORTCUT_GROUP_DEVICES) != 0)
            return THUNAR_SHORTCUT_SECTION_DEVICES;
          if ((group & THUNAR_SHORTCUT_GROUP_NETWORK) != 0)
            return THUNAR_SHORTCUT_SECTION_NETWORK;
          return THUNAR_SHORTCUT_SECTION_NONE;
        }



        static void
        thunar_shortcuts_model_set_order_id (ThunarShortcutsModel *model,
                                             ThunarShortcut       *shortcut,
                                             const gchar          *order_id)
        {
          const gchar * const *order = NULL;
          guint                n;

          g_free (shortcut->order_id);
          shortcut->order_id = g_strdup (order_id);
          shortcut->order_position = G_MAXINT;

          switch (thunar_shortcuts_model_get_section (shortcut->group))
            {
            case THUNAR_SHORTCUT_SECTION_PLACES:
              order = (const gchar * const *) model->places_order;
              break;
            case THUNAR_SHORTCUT_SECTION_DEVICES:
              order = (const gchar * const *) model->devices_order;
              break;
            default:
              return;
            }

          if (order != NULL)
            {
              for (n = 0; order[n] != NULL; ++n)
                if (g_strcmp0 (order[n], shortcut->order_id) == 0)
                  {
                    shortcut->order_position = n;
                    break;
                  }
            }
        }



        static gboolean
        thunar_shortcuts_model_order_contains (GPtrArray   *order,
                                               const gchar *order_id)
        {
          guint n;

          for (n = 0; n < order->len; ++n)
            if (g_strcmp0 (g_ptr_array_index (order, n), order_id) == 0)
              return TRUE;
          return FALSE;
        }



        static void
        thunar_shortcuts_model_save_order (ThunarShortcutsModel *model,
                                           ThunarShortcutSection section)
        {
          GPtrArray     *order;
          GList         *lp;
          ThunarShortcut *shortcut;
          gchar        **previous_order;
          gchar        **new_order;
          guint          n;

          if (section == THUNAR_SHORTCUT_SECTION_PLACES)
            previous_order = model->places_order;
          else if (section == THUNAR_SHORTCUT_SECTION_DEVICES)
            previous_order = model->devices_order;
          else
            return;

          order = g_ptr_array_new_with_free_func (g_free);
          for (lp = model->shortcuts; lp != NULL; lp = lp->next)
            {
              shortcut = lp->data;
              if (thunar_shortcuts_model_get_section (shortcut->group) != section
                  || (shortcut->group & THUNAR_SHORTCUT_GROUP_HEADER) != 0
                  || shortcut->order_id == NULL)
                continue;

              shortcut->order_position = order->len;
              g_ptr_array_add (order, g_strdup (shortcut->order_id));
            }

          /* Keep identifiers for temporarily disconnected devices. */
          if (section == THUNAR_SHORTCUT_SECTION_DEVICES && previous_order != NULL)
            for (n = 0; previous_order[n] != NULL; ++n)
              if (!thunar_shortcuts_model_order_contains (order, previous_order[n]))
                g_ptr_array_add (order, g_strdup (previous_order[n]));

          g_ptr_array_add (order, NULL);
          new_order = (gchar **) g_ptr_array_free (order, FALSE);

          if (section == THUNAR_SHORTCUT_SECTION_PLACES)
            {
              g_object_set (G_OBJECT (model->preferences),
                            "shortcuts-places-order", new_order,
                            NULL);
              g_strfreev (model->places_order);
              model->places_order = new_order;
            }
          else
            {
              g_object_set (G_OBJECT (model->preferences),
                            "shortcuts-devices-order", new_order,
                            NULL);
              g_strfreev (model->devices_order);
              model->devices_order = new_order;
            }
        }



        """
    )
    insert_before(
        path,
        "static gint\nthunar_shortcuts_model_sort_func",
        helper_code,
    )

    replace_function(
        path,
        "static gint\nthunar_shortcuts_model_sort_func",
        "static void\nthunar_shortcuts_model_add_shortcut_with_path",
        textwrap.dedent(
            """\
            static gint
            thunar_shortcuts_model_sort_func (gconstpointer shortcut_a,
                                              gconstpointer shortcut_b)
            {
              const ThunarShortcut *a = shortcut_a;
              const ThunarShortcut *b = shortcut_b;
              ThunarShortcutSection section_a;
              ThunarShortcutSection section_b;
              gboolean              header_a;
              gboolean              header_b;

              section_a = thunar_shortcuts_model_get_section (a->group);
              section_b = thunar_shortcuts_model_get_section (b->group);
              if (section_a != section_b)
                return section_a - section_b;

              if (section_a == THUNAR_SHORTCUT_SECTION_PLACES
                  || section_a == THUNAR_SHORTCUT_SECTION_DEVICES)
                {
                  header_a = (a->group & THUNAR_SHORTCUT_GROUP_HEADER) != 0;
                  header_b = (b->group & THUNAR_SHORTCUT_GROUP_HEADER) != 0;
                  if (header_a != header_b)
                    return header_a ? -1 : 1;

                  if (!header_a && a->order_position != b->order_position)
                    return a->order_position > b->order_position ? 1 : -1;
                }

              /* Preserve the default subtype order for entries not yet persisted. */
              if (a->group != b->group)
                return a->group - b->group;

              if (a->sort_id != b->sort_id)
                return a->sort_id > b->sort_id ? 1 : -1;

              if (a->device != NULL && b->device != NULL)
                return thunar_device_compare_by_name (a->device, b->device);

              return g_strcmp0 (a->name, b->name);
            }"""
        ),
    )

    replace_once(
        path,
        """  ThunarShortcut       *shortcut;
  ThunarFile           *file;

  _thunar_return_if_fail (G_IS_FILE (file_path));""",
        """  ThunarShortcut       *shortcut;
  ThunarFile           *file;
  gchar                *uri;
  gchar                *order_id;

  _thunar_return_if_fail (G_IS_FILE (file_path));""",
    )

    replace_once(
        path,
        """  shortcut->sort_id = row_num;
  shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
  shortcut->name = g_strdup (name);

  /* append the shortcut to the list */""",
        """  shortcut->sort_id = row_num;
  shortcut->hidden = thunar_shortcuts_model_get_hidden (model, shortcut);
  shortcut->name = g_strdup (name);
  uri = g_file_get_uri (file_path);
  order_id = g_strconcat ("bookmark:", uri, NULL);
  thunar_shortcuts_model_set_order_id (model, shortcut, order_id);
  g_free (order_id);
  g_free (uri);

  /* append the shortcut to the list */""",
    )

    replace_once(
        path,
        """  thunar_util_load_bookmarks (model->bookmarks_file,
                              thunar_shortcuts_model_load_line,
                              model);

  /* update the visibility */""",
        """  thunar_util_load_bookmarks (model->bookmarks_file,
                              thunar_shortcuts_model_load_line,
                              model);

  if (model->places_order == NULL)
    thunar_shortcuts_model_save_order (model, THUNAR_SHORTCUT_SECTION_PLACES);

  /* update the visibility */""",
    )

    replace_once(
        path,
        """  ThunarShortcut *shortcut;
  GFile          *mount_point;

  _thunar_return_if_fail (device_monitor == NULL || THUNAR_DEVICE_MONITOR (device_monitor));""",
        """  ThunarShortcut *shortcut;
  GFile          *mount_point;
  gchar          *device_id;
  gchar          *order_id;

  _thunar_return_if_fail (device_monitor == NULL || THUNAR_DEVICE_MONITOR (device_monitor));""",
    )

    replace_once(
        path,
        """    case THUNAR_DEVICE_KIND_MOUNT_REMOTE:
      shortcut->group = THUNAR_SHORTCUT_GROUP_NETWORK_MOUNTS;
      break;
    }

  /* insert in the model */""",
        """    case THUNAR_DEVICE_KIND_MOUNT_REMOTE:
      shortcut->group = THUNAR_SHORTCUT_GROUP_NETWORK_MOUNTS;
      break;
    }

  if ((shortcut->group & THUNAR_SHORTCUT_GROUP_DEVICES) != 0)
    {
      device_id = thunar_device_get_identifier (device);
      if (device_id == NULL)
        device_id = thunar_device_get_name (device);
      if (device_id != NULL)
        {
          order_id = g_strconcat ("device:", device_id, NULL);
          thunar_shortcuts_model_set_order_id (model, shortcut, order_id);
          g_free (order_id);
        }
      g_free (device_id);
    }

  /* insert in the model */""",
    )

    replace_once(
        path,
        """  g_free (shortcut->name);
  g_free (shortcut->tooltip);

  /* release the shortcut itself */""",
        """  g_free (shortcut->name);
  g_free (shortcut->tooltip);
  g_free (shortcut->order_id);

  /* release the shortcut itself */""",
    )

    replace_function(
        path,
        "gboolean\nthunar_shortcuts_model_drop_possible",
        "/**\n * thunar_shortcuts_model_add:",
        textwrap.dedent(
            """\
            gboolean
            thunar_shortcuts_model_drop_possible (ThunarShortcutsModel *model,
                                                  GtkTreePath          *src_path,
                                                  GtkTreePath          *dst_path)
            {
              ThunarShortcut        *source = NULL;
              ThunarShortcut        *destination;
              ThunarShortcut        *previous;
              ThunarShortcutSection  section;
              gint                   dst_index;

              _thunar_return_val_if_fail (THUNAR_IS_SHORTCUTS_MODEL (model), FALSE);
              _thunar_return_val_if_fail (gtk_tree_path_get_depth (dst_path) > 0, FALSE);

              dst_index = gtk_tree_path_get_indices (dst_path)[0];
              destination = g_list_nth_data (model->shortcuts, dst_index);
              if (destination == NULL)
                return FALSE;

              /* URI drops create bookmarks and may be inserted anywhere in Places. */
              if (src_path == NULL)
                {
                  if (thunar_shortcuts_model_get_section (destination->group)
                        == THUNAR_SHORTCUT_SECTION_PLACES
                      && (destination->group & THUNAR_SHORTCUT_GROUP_HEADER) == 0)
                    return TRUE;
                  return destination->group == THUNAR_SHORTCUT_GROUP_DEVICES_HEADER;
                }

              _thunar_return_val_if_fail (gtk_tree_path_get_depth (src_path) > 0, FALSE);
              source = g_list_nth_data (model->shortcuts,
                                        gtk_tree_path_get_indices (src_path)[0]);
              if (source == NULL || (source->group & THUNAR_SHORTCUT_GROUP_HEADER) != 0)
                return FALSE;

              section = thunar_shortcuts_model_get_section (source->group);
              if (section != THUNAR_SHORTCUT_SECTION_PLACES
                  && section != THUNAR_SHORTCUT_SECTION_DEVICES)
                return FALSE;

              if ((destination->group & THUNAR_SHORTCUT_GROUP_HEADER) == 0)
                return thunar_shortcuts_model_get_section (destination->group) == section;

              /* The following section header is the insertion point after the
               * final item of a section.
               */
              if (dst_index > 0)
                {
                  previous = g_list_nth_data (model->shortcuts, dst_index - 1);
                  return previous != NULL
                         && thunar_shortcuts_model_get_section (previous->group) == section;
                }

              return FALSE;
            }"""
        ),
    )

    replace_once(
        path,
        """  ThunarShortcut *shortcut;
  GFile          *location;
  GList          *lp;
  guint           position = 0;""",
        """  ThunarShortcut *shortcut;
  GFile          *location;
  GList          *lp;
  gchar          *uri;
  gchar          *order_id;
  guint           position = 0;""",
    )

    replace_once(
        path,
        """  shortcut->group = THUNAR_SHORTCUT_GROUP_PLACES_BOOKMARKS;
  shortcut->location = G_FILE (g_object_ref (G_OBJECT (location)));

  if (thunar_shortcuts_model_local_file (location))""",
        """  shortcut->group = THUNAR_SHORTCUT_GROUP_PLACES_BOOKMARKS;
  shortcut->location = G_FILE (g_object_ref (G_OBJECT (location)));
  uri = g_file_get_uri (location);
  order_id = g_strconcat ("bookmark:", uri, NULL);
  thunar_shortcuts_model_set_order_id (model, shortcut, order_id);
  g_free (order_id);
  g_free (uri);

  if (thunar_shortcuts_model_local_file (location))""",
    )

    replace_once(
        path,
        """ * @model : a #ThunarShortcutstModel.
 * @path  : a #GtkTreePath.
 *
 * Determines whether a drop is possible before the given @path, at the same depth
 * as @path. I.e., can we drop data at that location. @path does not have to exist;
 * the return value will almost certainly be FALSE if the parent of @path doesn't
 * exist, though.
""",
        """ * @model    : a #ThunarShortcutsModel.
 * @src_path : the source path for an internal move, or %NULL for a URI drop.
 * @dst_path : the proposed insertion path.
 *
 * Determines whether an internal move can remain inside its Places or Devices
 * section, or whether an external URI can be inserted into Places.
 *
 * Return value: %TRUE if data can be dropped before @dst_path, else %FALSE.
""",
    )

    replace_once(
        path,
        """ *
 * Return value: %TRUE if it's possible to drop data before @path, else %FALSE.
 **/
gboolean
thunar_shortcuts_model_drop_possible""",
        """ **/
gboolean
thunar_shortcuts_model_drop_possible""",
    )

    replace_once(
        path,
        """  /* the shortcuts list was changed, so write the gtk bookmarks file */
  thunar_shortcuts_model_save (model);
}



/**
 * thunar_shortcuts_model_move:""",
        """  /* persist both the GTK bookmarks and their integrated Places order */
  thunar_shortcuts_model_save (model);
  thunar_shortcuts_model_save_order (model, THUNAR_SHORTCUT_SECTION_PLACES);
}



/**
 * thunar_shortcuts_model_move:""",
    )

    replace_once(
        path,
        """  gint            idx;
  gint            n_shortcuts;

  _thunar_return_if_fail (THUNAR_IS_SHORTCUTS_MODEL (model));""",
        """  gint            idx;
  gint            n_shortcuts;
  ThunarShortcutSection section;

  _thunar_return_if_fail (THUNAR_IS_SHORTCUTS_MODEL (model));""",
    )

    replace_once(
        path,
        """  if (G_UNLIKELY (index_src == index_dst))
    return;

  /* generate the order for the rows prior the dst/src rows */""",
        """  if (G_UNLIKELY (index_src == index_dst))
    return;

  shortcut = g_list_nth_data (model->shortcuts, index_src);
  section = thunar_shortcuts_model_get_section (shortcut->group);

  /* generate the order for the rows prior the dst/src rows */""",
    )

    replace_once(
        path,
        """  /* the shortcuts list was changed, so write the gtk bookmarks file */
  thunar_shortcuts_model_save (model);
}



/**
 * thunar_shortcuts_model_remove:""",
        """  /* Keep GTK bookmarks and the relevant section order synchronized. */
  if (section == THUNAR_SHORTCUT_SECTION_PLACES)
    thunar_shortcuts_model_save (model);
  thunar_shortcuts_model_save_order (model, section);
}



/**
 * thunar_shortcuts_model_remove:""",
    )

    replace_once(
        path,
        """      /* the shortcuts list was changed, so write the gtk bookmarks file */
      if (needs_save)
        thunar_shortcuts_model_save (model);

      /* update header visibility */""",
        """      /* the shortcuts list was changed, so write the gtk bookmarks file */
      if (needs_save)
        {
          thunar_shortcuts_model_save (model);
          thunar_shortcuts_model_save_order (model, THUNAR_SHORTCUT_SECTION_PLACES);
        }

      /* update header visibility */""",
    )


def patch_view(source: pathlib.Path) -> None:
    path = source / "thunar" / "thunar-shortcuts-view.c"

    replace_once(
        path,
        """static GtkTreePath   *thunar_shortcuts_view_compute_drop_position        (ThunarShortcutsView      *view,
                                                                          gint                      x,
                                                                          gint                      y);""",
        """static GtkTreePath   *thunar_shortcuts_view_compute_drop_position        (ThunarShortcutsView      *view,
                                                                          gint                      x,
                                                                          gint                      y,
                                                                          GtkTreePath              *src_path);
static GtkTreePath   *thunar_shortcuts_view_convert_drop_path_to_child     (GtkTreeModel             *model,
                                                                          GtkTreePath              *child_src_path,
                                                                          GtkTreePath              *dst_path);""",
    )

    replace_function(
        path,
        "static gboolean\nthunar_shortcuts_view_drag_drop",
        "static gboolean\nthunar_shortcuts_view_drag_motion",
        textwrap.dedent(
            """\
            static gboolean
            thunar_shortcuts_view_drag_drop (GtkWidget      *widget,
                                             GdkDragContext *context,
                                             gint            x,
                                             gint            y,
                                             guint           timestamp)
            {
              ThunarShortcutsView *view = THUNAR_SHORTCUTS_VIEW (widget);
              GtkTreeSelection    *selection;
              GtkTreeModel        *model;
              GtkTreePath         *dst_path = NULL;
              GtkTreePath         *src_path;
              GtkTreeIter          iter;
              GdkAtom              target;
              GtkTreeModel        *child_model;
              GtkTreePath         *child_dst_path;
              GtkTreePath         *child_src_path;
              gboolean             succeed = FALSE;

              _thunar_return_val_if_fail (THUNAR_IS_SHORTCUTS_VIEW (view), FALSE);

              target = gtk_drag_dest_find_target (widget, context, NULL);
              if (G_LIKELY (target == gdk_atom_intern_static_string ("text/uri-list")))
                {
                  view->drop_occurred = TRUE;
                  gtk_drag_get_data (widget, context, target, timestamp);
                }
              else if (target == gdk_atom_intern_static_string ("GTK_TREE_MODEL_ROW"))
                {
                  selection = gtk_tree_view_get_selection (GTK_TREE_VIEW (view));
                  if (gtk_tree_selection_get_selected (selection, &model, &iter))
                    {
                      src_path = gtk_tree_model_get_path (model, &iter);
                      dst_path = thunar_shortcuts_view_compute_drop_position (view, x, y, src_path);

                      if (dst_path != NULL)
                        {
                          child_src_path = gtk_tree_model_filter_convert_path_to_child_path (
                              GTK_TREE_MODEL_FILTER (model), src_path);
                          child_dst_path = thunar_shortcuts_view_convert_drop_path_to_child (
                              model, child_src_path, dst_path);
                          child_model = gtk_tree_model_filter_get_model (GTK_TREE_MODEL_FILTER (model));

                          if (child_src_path != NULL && child_dst_path != NULL)
                            {
                              if (gtk_tree_path_compare (child_src_path, child_dst_path) < 0)
                                gtk_tree_path_prev (child_dst_path);
                              if (gtk_tree_path_compare (src_path, dst_path) < 0)
                                gtk_tree_path_prev (dst_path);

                              thunar_shortcuts_model_move (THUNAR_SHORTCUTS_MODEL (child_model),
                                                           child_src_path, child_dst_path);
                              gtk_tree_selection_select_path (selection, dst_path);
                              succeed = TRUE;
                            }

                          if (child_src_path != NULL)
                            gtk_tree_path_free (child_src_path);
                          if (child_dst_path != NULL)
                            gtk_tree_path_free (child_dst_path);
                        }

                      gtk_tree_path_free (src_path);
                    }

                  if (dst_path != NULL)
                    gtk_tree_path_free (dst_path);
                  gtk_drag_finish (context, succeed, FALSE, timestamp);
                }
              else
                {
                  return FALSE;
                }

              return TRUE;
            }"""
        ),
    )

    replace_function(
        path,
        "static gboolean\nthunar_shortcuts_view_drag_motion",
        "static void\nthunar_shortcuts_view_drag_leave",
        textwrap.dedent(
            """\
            static gboolean
            thunar_shortcuts_view_drag_motion (GtkWidget      *widget,
                                               GdkDragContext *context,
                                               gint            x,
                                               gint            y,
                                               guint           timestamp)
            {
              GtkTreeViewDropPosition position = GTK_TREE_VIEW_DROP_BEFORE;
              ThunarShortcutsView    *view = THUNAR_SHORTCUTS_VIEW (widget);
              GdkDragAction           action = 0;
              GtkTreeModel           *model;
              GtkTreePath            *path = NULL;
              GtkTreePath            *src_path;
              GtkTreeSelection       *selection;
              GtkTreeIter             iter;
              GdkAtom                 target;

              g_object_set (G_OBJECT (view->icon_renderer), "drop-file", NULL, NULL);

              target = gtk_drag_dest_find_target (widget, context, NULL);
              if (target == gdk_atom_intern_static_string ("text/uri-list"))
                {
                  if (G_UNLIKELY (!view->drop_data_ready))
                    {
                      gtk_drag_get_data (widget, context, target, timestamp);
                      return TRUE;
                    }
                  thunar_shortcuts_view_compute_drop_actions (
                      view, context, x, y, &path, &action, &position);
                }
              else if (target == gdk_atom_intern_static_string ("GTK_TREE_MODEL_ROW"))
                {
                  if (gdk_drag_context_get_suggested_action (context) == GDK_ACTION_MOVE
                      || (gdk_drag_context_get_actions (context) & GDK_ACTION_MOVE) != 0)
                    action = GDK_ACTION_MOVE;
                  else
                    return FALSE;

                  model = gtk_tree_view_get_model (GTK_TREE_VIEW (view));
                  selection = gtk_tree_view_get_selection (GTK_TREE_VIEW (view));
                  if (!gtk_tree_selection_get_selected (selection, &model, &iter))
                    return FALSE;

                  src_path = gtk_tree_model_get_path (model, &iter);
                  path = thunar_shortcuts_view_compute_drop_position (view, x, y, src_path);
                  gtk_tree_path_free (src_path);
                  if (path == NULL)
                    return FALSE;

                  if (gtk_tree_path_get_indices (path)[0]
                      >= gtk_tree_model_iter_n_children (model, NULL))
                    {
                      position = GTK_TREE_VIEW_DROP_AFTER;
                      gtk_tree_path_prev (path);
                    }
                }
              else
                {
                  return FALSE;
                }

              if (G_LIKELY (path != NULL))
                {
                  gtk_tree_view_set_drag_dest_row (GTK_TREE_VIEW (view), path, position);
                  gtk_tree_path_free (path);
                }
              else
                {
                  gtk_tree_view_set_drag_dest_row (GTK_TREE_VIEW (view), NULL, position);
                }

              gdk_drag_status (context, action, timestamp);
              return TRUE;
            }"""
        ),
    )

    replace_once(
        path,
        """      path = thunar_shortcuts_view_compute_drop_position (view, x, y);

      if (path == NULL)""",
        """      path = thunar_shortcuts_view_compute_drop_position (view, x, y, NULL);

      if (path == NULL)""",
    )

    replace_function(
        path,
        "static GtkTreePath*\nthunar_shortcuts_view_compute_drop_position",
        "static void\nthunar_shortcuts_view_drop_uri_list",
        textwrap.dedent(
            """\
            static gboolean
            thunar_shortcuts_view_groups_share_section (guint group_a,
                                                        guint group_b)
            {
              return (((group_a & THUNAR_SHORTCUT_GROUP_PLACES) != 0
                       && (group_b & THUNAR_SHORTCUT_GROUP_PLACES) != 0)
                      || ((group_a & THUNAR_SHORTCUT_GROUP_DEVICES) != 0
                          && (group_b & THUNAR_SHORTCUT_GROUP_DEVICES) != 0)
                      || ((group_a & THUNAR_SHORTCUT_GROUP_NETWORK) != 0
                          && (group_b & THUNAR_SHORTCUT_GROUP_NETWORK) != 0));
            }



            static GtkTreePath*
            thunar_shortcuts_view_convert_drop_path_to_child (GtkTreeModel *model,
                                                              GtkTreePath  *child_src_path,
                                                              GtkTreePath  *dst_path)
            {
              GtkTreeModel *child_model;
              GtkTreePath  *child_dst_path;
              GtkTreeIter   iter;
              guint         source_group;
              guint         destination_group;

              if (gtk_tree_path_get_indices (dst_path)[0]
                  < gtk_tree_model_iter_n_children (model, NULL))
                return gtk_tree_model_filter_convert_path_to_child_path (
                    GTK_TREE_MODEL_FILTER (model), dst_path);

              if (child_src_path == NULL)
                return NULL;

              child_model = gtk_tree_model_filter_get_model (GTK_TREE_MODEL_FILTER (model));
              if (!gtk_tree_model_get_iter (child_model, &iter, child_src_path))
                return NULL;
              gtk_tree_model_get (child_model, &iter,
                                  THUNAR_SHORTCUTS_MODEL_COLUMN_GROUP, &source_group,
                                  -1);

              child_dst_path = gtk_tree_path_copy (child_src_path);
              gtk_tree_path_next (child_dst_path);
              while (gtk_tree_model_get_iter (child_model, &iter, child_dst_path))
                {
                  gtk_tree_model_get (child_model, &iter,
                                      THUNAR_SHORTCUTS_MODEL_COLUMN_GROUP, &destination_group,
                                      -1);
                  if (!thunar_shortcuts_view_groups_share_section (source_group,
                                                                  destination_group))
                    return child_dst_path;
                  gtk_tree_path_next (child_dst_path);
                }

              return child_dst_path;
            }



            static GtkTreePath*
            thunar_shortcuts_view_compute_drop_position (ThunarShortcutsView *view,
                                                         gint                 x,
                                                         gint                 y,
                                                         GtkTreePath         *src_path)
            {
              GtkTreeViewColumn *column;
              GtkTreeModel      *model;
              GdkRectangle       area;
              GtkTreePath       *path;
              gint               n_rows;
              gboolean           result;
              GtkTreePath       *child_path;
              GtkTreePath       *child_src_path = NULL;
              GtkTreePath       *last_path;
              GtkTreeModel      *child_model;

              _thunar_return_val_if_fail (gtk_tree_view_get_model (GTK_TREE_VIEW (view)) != NULL, NULL);
              _thunar_return_val_if_fail (THUNAR_IS_SHORTCUTS_VIEW (view), NULL);

              model = gtk_tree_view_get_model (GTK_TREE_VIEW (view));
              child_model = gtk_tree_model_filter_get_model (GTK_TREE_MODEL_FILTER (model));
              n_rows = gtk_tree_model_iter_n_children (model, NULL);

              if (src_path != NULL)
                child_src_path = gtk_tree_model_filter_convert_path_to_child_path (
                    GTK_TREE_MODEL_FILTER (model), src_path);

              if (gtk_tree_view_get_path_at_pos (GTK_TREE_VIEW (view), x, y,
                                                 &path, &column, &x, &y))
                {
                  gtk_tree_view_get_background_area (GTK_TREE_VIEW (view), path, column, &area);
                  if (y >= area.height / 2)
                    gtk_tree_path_next (path);

                  for (; gtk_tree_path_get_indices (path)[0] < n_rows;
                       gtk_tree_path_next (path))
                    {
                      child_path = gtk_tree_model_filter_convert_path_to_child_path (
                          GTK_TREE_MODEL_FILTER (model), path);
                      result = thunar_shortcuts_model_drop_possible (
                          THUNAR_SHORTCUTS_MODEL (child_model), child_src_path, child_path);
                      gtk_tree_path_free (child_path);
                      if (result)
                        {
                          if (child_src_path != NULL)
                            gtk_tree_path_free (child_src_path);
                          return path;
                        }
                      if (child_src_path != NULL)
                        break;
                    }

                  /* A filtered model has no directly convertible path after its
                   * final visible row. Validate that insertion point against the
                   * last visible row; the drop handler resolves the full-model
                   * section boundary, including hidden rows.
                   */
                  if (child_src_path != NULL
                      && gtk_tree_path_get_indices (path)[0] >= n_rows
                      && n_rows > 0)
                    {
                      last_path = gtk_tree_path_new_from_indices (n_rows - 1, -1);
                      child_path = gtk_tree_model_filter_convert_path_to_child_path (
                          GTK_TREE_MODEL_FILTER (model), last_path);
                      gtk_tree_path_free (last_path);
                      result = thunar_shortcuts_model_drop_possible (
                          THUNAR_SHORTCUTS_MODEL (child_model), child_src_path, child_path);
                      gtk_tree_path_free (child_path);
                      if (result)
                        {
                          gtk_tree_path_free (child_src_path);
                          return path;
                        }
                    }

                  gtk_tree_path_free (path);
                }

              if (child_src_path != NULL)
                gtk_tree_path_free (child_src_path);
              return NULL;
            }"""
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    if args.source_dir.exists():
        raise SystemExit(f"source directory already exists: {args.source_dir}")

    run(
        "git",
        "clone",
        "--depth=1",
        "--branch",
        UPSTREAM_TAG,
        UPSTREAM_URL,
        str(args.source_dir),
    )

    patch_preferences(args.source_dir)
    patch_model_header(args.source_dir)
    patch_model(args.source_dir)
    patch_view(args.source_dir)

    run("git", "diff", "--check", cwd=args.source_dir)
    patch = subprocess.check_output(
        ["git", "diff", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/"],
        cwd=args.source_dir,
    )
    if not patch:
        raise SystemExit("patch generation produced an empty diff")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patch)


if __name__ == "__main__":
    main()
