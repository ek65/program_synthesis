from api_utils import API
from synth_utils import *

import plotly.graph_objects as go
import networkx as nx
from collections import defaultdict
import textwrap

def wrap_text(text, width=40):
    return "<br>".join(textwrap.wrap(text, width=width))

import json
import ipywidgets as widgets
from IPython.display import display
from IPython.display import clear_output

class EditLogger:
    def __init__(self, edited: list = []):
        self.edited = edited

    def add(self, id):
        self.edited.append(id)

def edit_interface(act, api=None, edit_logger: EditLogger = EditLogger()):
    """
    Creates a clean, four-tab editing interface for an Act.
    
    Tabs:
      - Edit Action: select an existing action, update its API (text), description, termination text, and timing.
      - Edit Edge: select an existing edge, update its precondition description and timing.
      - Add Action: add a new action with API, description, termination text, and timing.
      - Add Edge: add a new edge by selecting a source and target action and providing precondition and timing.
      
    The interface is displayed above the interactive FSM.
    """
    # Helper: update the graph drawing (replace with your own function)
    graph_output = widgets.Output()

    def draw_graph():
        with graph_output:
            graph_output.clear_output(wait=True)
            interactive_show(act)

    # --- EDIT ACTION TAB ---
    # Dropdown to select action node (by id)
    action_ids = [str(a.id) for a in act.nodes]
    edit_action_selector = widgets.Dropdown(options=action_ids or [''], description='Action ID:')
    
    # Widgets to edit action properties
    edit_api = widgets.Text(value='', description='API:')
    edit_info = widgets.Textarea(value='', description='Description:')
    edit_term = widgets.Textarea(value='', description='Termination:')
    edit_timing = widgets.Textarea(value='', description='Timing (JSON):')
    
    update_action_button = widgets.Button(description="Update Action", button_style='success')
    delete_action_button = widgets.Button(description="Delete Action", button_style='danger')
    
    # When an action is selected, update fields.
    def refresh_action_fields(*args):
        # find selected action by id
        selected_id = edit_action_selector.value
        action = next((a for a in act.nodes if str(a.id) == selected_id), None)
        if action:
            edit_api.value = action.api.ref() if hasattr(action.api, 'ref') else ""
            edit_info.value = action.info
            edit_term.value = action.termination.info if hasattr(action.termination, 'info') else ""
            try:
                edit_timing.value = json.dumps(action.t, indent=2)
            except Exception:
                edit_timing.value = str(action.t)
    
    edit_action_selector.observe(refresh_action_fields, names='value')
    refresh_action_fields()
    
    def on_update_action(b):
        selected_id = edit_action_selector.value
        action = next((a for a in act.nodes if str(a.id) == selected_id), None)
        if not action:
            return
        # update API reference (for simplicity, we assume API is just stored as a string in a lambda)
        new_api = edit_api.value
        action.api.ref = lambda new_api=new_api: new_api
        action.info = edit_info.value
        if hasattr(action.termination, 'info'):
            action.termination.info = edit_term.value
        # Update timing (attempt to parse JSON)
        try:
            action.t = json.loads(edit_timing.value)
        except Exception as e:
            print("Timing JSON parse error:", e)
        refresh_action_fields()
        update_action_selector_options()
        draw_graph()
        edit_logger.add(selected_id)
    
    update_action_button.on_click(on_update_action)
    
    def on_delete_action(b):
        selected_id = edit_action_selector.value
        act.nodes = [a for a in act.nodes if str(a.id) != selected_id]
        # Remove any edge that touches this action
        act.edges = [e for e in act.edges if str(e.prev) != selected_id and str(e.next) != selected_id]
        update_action_selector_options()
        update_edge_selector_options()
        refresh_action_fields()
        draw_graph()
        edit_logger.add(selected_id)
    
    delete_action_button.on_click(on_delete_action)
    
    edit_action_tab = widgets.VBox([
        widgets.HTML("<h3>Edit Action</h3>"),
        edit_action_selector,
        # edit_api,
        edit_info,
        edit_term,
        edit_timing,
        widgets.HBox([update_action_button, delete_action_button])
    ])
    
    # --- EDIT EDGE TAB ---
    # Dropdown to select an edge (by its id)
    edge_ids = [str(e.id) for e in act.edges]
    edit_edge_selector = widgets.Dropdown(options=edge_ids or [''], description='Edge ID:')
    
    # Widgets to edit edge properties
    edit_edge_precond = widgets.Textarea(value='', description='Precondition:')
    edit_edge_timing = widgets.Textarea(value='', description='Timing (JSON):')
    
    update_edge_button = widgets.Button(description="Update Edge", button_style='success')
    delete_edge_button = widgets.Button(description="Delete Edge", button_style='danger')
    
    def refresh_edge_fields(*args):
        selected_edge_id = edit_edge_selector.value
        edge = next((e for e in act.edges if str(e.id) == selected_edge_id), None)
        if edge:
            edit_edge_precond.value = edge.precondition.info if hasattr(edge.precondition, 'info') else ""
            try:
                edit_edge_timing.value = json.dumps(edge.t, indent=2)
            except Exception:
                edit_edge_timing.value = str(edge.t)
    
    edit_edge_selector.observe(refresh_edge_fields, names='value')
    refresh_edge_fields()
    
    def on_update_edge(b):
        selected_edge_id = edit_edge_selector.value
        edge = next((e for e in act.edges if str(e.id) == selected_edge_id), None)
        if not edge:
            return
        if hasattr(edge.precondition, 'info'):
            edge.precondition.info = edit_edge_precond.value
        try:
            edge.t = json.loads(edit_edge_timing.value)
        except Exception as e:
            print("Edge timing parse error:", e)
        refresh_edge_fields()
        update_edge_selector_options()
        draw_graph()
        edit_logger.add(selected_edge_id)
    
    update_edge_button.on_click(on_update_edge)
    
    def on_delete_edge(b):
        selected_edge_id = edit_edge_selector.value
        act.edges = [e for e in act.edges if str(e.id) != selected_edge_id]
        update_edge_selector_options()
        refresh_edge_fields()
        draw_graph()
        edit_logger.add(selected_edge_id)
    
    delete_edge_button.on_click(on_delete_edge)
    
    edit_edge_tab = widgets.VBox([
        widgets.HTML("<h3>Edit Edge</h3>"),
        edit_edge_selector,
        edit_edge_precond,
        edit_edge_timing,
        widgets.HBox([update_edge_button, delete_edge_button])
    ])
    
    # --- ADD ACTION TAB ---
    add_api = widgets.Text(value='', description='API:')
    add_info = widgets.Textarea(value='', description='Description:')
    add_term = widgets.Textarea(value='', description='Termination:')
    add_timing = widgets.Textarea(value='', description='Timing (JSON):')
    add_action_button = widgets.Button(description="Add Action", button_style='info')
    
    def on_add_action(b):
        # determine new id: assume integer ids; use max + 1 or 1 if no actions
        try:
            new_id = max([int(a.id) for a in act.nodes]) + 1 if act.nodes else 1
        except Exception:
            new_id = 1
        # Create a new Action.
        # Note: The Action constructor will wrap termination into a Termination if needed.
        try:
            t_val = json.loads(add_timing.value)
        except Exception:
            t_val = add_timing.value
        new_action = Action(new_id, add_api.value, add_info.value, add_term.value, t_val, api=api, act=act)
        act.nodes.append(new_action)
        update_action_selector_options()
        # Clear add fields
        add_api.value = ""
        add_info.value = ""
        add_term.value = ""
        add_timing.value = ""
        draw_graph()
        edit_logger.add(new_id)
    
    add_action_button.on_click(on_add_action)
    
    add_action_tab = widgets.VBox([
        widgets.HTML("<h3>Add New Action</h3>"),
        # add_api,
        add_info,
        add_term,
        add_timing,
        add_action_button
    ])
    
    # --- ADD EDGE TAB ---
    # Dropdowns to select from and to nodes
    def get_node_options():
        return [str(a.id) for a in act.nodes]
    
    add_edge_from = widgets.Dropdown(options=get_node_options(), description='From:')
    add_edge_to = widgets.Dropdown(options=get_node_options(), description='To:')
    add_edge_precond = widgets.Textarea(value='', description='Precondition:')
    add_edge_timing = widgets.Textarea(value='', description='Timing (JSON):')
    add_edge_button = widgets.Button(description="Add Edge", button_style='info')
    
    def on_add_edge(b):
        # determine new edge id
        try:
            new_edge_id = max([int(e.id) for e in act.edges]) + 1 if act.edges else 1
        except Exception:
            new_edge_id = 1
        from_id = add_edge_from.value
        to_id = add_edge_to.value
        try:
            t_val = json.loads(add_edge_timing.value)
        except Exception:
            t_val = add_edge_timing.value
        # Create a new Transition. (Precondition is wrapped into a Precondition instance by its constructor.)
        new_edge = Transition(new_edge_id, from_id, to_id, add_edge_precond.value, t_val, api=api, act=act)
        act.edges.append(new_edge)
        update_edge_selector_options()
        add_edge_precond.value = ""
        add_edge_timing.value = ""
        draw_graph()
        edit_logger.add(new_edge_id)
    
    add_edge_button.on_click(on_add_edge)
    
    add_edge_tab = widgets.VBox([
        widgets.HTML("<h3>Add New Edge</h3>"),
        widgets.HBox([add_edge_from, add_edge_to]),
        add_edge_precond,
        add_edge_timing,
        add_edge_button
    ])
    
    # --- Helper functions to update dropdown options ---
    def update_action_selector_options():
        new_options = [str(a.id) for a in act.nodes]
        edit_action_selector.options = new_options or ['']
        # Also update the "from" and "to" options in add edge tab:
        node_opts = get_node_options()
        add_edge_from.options = node_opts or ['']
        add_edge_to.options = node_opts or ['']
    
    def update_edge_selector_options():
        new_options = [str(e.id) for e in act.edges]
        edit_edge_selector.options = new_options or ['']
    
    update_action_selector_options()
    update_edge_selector_options()
    
    # --- Assemble the tabs ---
    tab_contents = {
        'Edit Action': edit_action_tab,
        'Edit Edge': edit_edge_tab,
        'Add Action': add_action_tab,
        'Add Edge': add_edge_tab
    }
    children = [tab_contents[key] for key in tab_contents]
    tab_widget = widgets.Tab(children=children)
    for idx, key in enumerate(tab_contents):
        tab_widget.set_title(idx, key)
    
    interface = widgets.VBox([graph_output, tab_widget])
    display(interface)
    draw_graph()

def interactive_show(act):
    """
    Displays an interactive FSM in a Jupyter Notebook.
    
    Actions (blue circles) and transitions (red diamonds) are shown as nodes.
    Hover text shows additional details for each node.
    The layout positions nodes based on a BFS traversal (root at the left, deeper nodes to the right).
    """
    # Build a directed graph from the act nodes and edges
    G = nx.DiGraph()
    for action in act.nodes:
        G.add_node(str(action.id))
    for trans in act.edges:
        G.add_edge(str(trans.prev), str(trans.next))
    
    if not act.nodes:
        print("No actions to display.")
        return

    # Use the first action as the root for BFS ordering.
    root = str(act.nodes[0].id)
    
    # Compute BFS levels for each action node
    levels = defaultdict(list)
    for node in G.nodes():
        try:
            level = nx.shortest_path_length(G, source=root, target=node)
        except nx.NetworkXNoPath:
            level = max(levels.keys(), default=0) + 1
        levels[level].append(node)
    
    # Assign positions: x = level, y = evenly spaced in that level (centered at 0)
    positions = {}
    for level, nodes in levels.items():
        count = len(nodes)
        for i, node in enumerate(sorted(nodes)):
            y = i - (count - 1) / 2
            positions[node] = (level, y)
    
    # Prepare data for action nodes
    action_x, action_y = [], []
    # Preview text includes the ID and API reference
    action_preview = [f"ID: {action.id}<br>{wrap_text(action.api.ref(), width=40)}" for action in act.nodes]
    # Hover text now shows description and termination information in the requested format.
    action_hover = [
        f"<b>Action ID:</b> {action.id}<br><b>Description:</b> {wrap_text(action.info, width=40)}<br><b>Termination:</b> {wrap_text(action.termination.info, width=40)}"
        for action in act.nodes
    ]
    
    for action in act.nodes:
        node_id = str(action.id)
        x, y = positions.get(node_id, (0, 0))
        action_x.append(x)
        action_y.append(y)
    
    # Prepare data for transition nodes (placed at midpoints)
    transition_x, transition_y = [], []
    transition_hover, transition_preview = [], []  # Adding preview for transition IDs.
    transition_edges = []
    for trans in act.edges:
        src_id = str(trans.prev)
        tgt_id = str(trans.next)
        if src_id in positions and tgt_id in positions:
            src_pos = positions[src_id]
            tgt_pos = positions[tgt_id]
            mid_x = (src_pos[0] + tgt_pos[0]) / 2
            mid_y = (src_pos[1] + tgt_pos[1]) / 2
            transition_x.append(mid_x)
            transition_y.append(mid_y)
            transition_hover.append(
                f"<b>Transition ID:</b> {trans.id}<br><b>Precondition:</b> {wrap_text(trans.precondition.info, width=40)}"
            )
            transition_preview.append(f"ID: {trans.id}")
            transition_edges.append((src_pos, (mid_x, mid_y), tgt_pos))
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Action nodes: blue squares with preview text
    fig.add_trace(go.Scatter(
        x=action_x,
        y=action_y,
        mode='markers+text',  # Show both markers and text
        text=action_preview,  # Preview content includes ID and API reference
        textposition='top center',  # Adjust position as needed
        hovertext=action_hover,  # Hover text shows description and termination details
        marker=dict(color="#A0CBE8", symbol='square', size=20),
        hoverinfo='text',
        name='Actions'
    ))
    
    # Transition nodes: red diamonds with preview text
    fig.add_trace(go.Scatter(
        x=transition_x,
        y=transition_y,
        mode='markers+text',
        marker=dict(color="#FFDAC1", symbol='circle', size=15),
        text=transition_preview,  # Preview shows the transition ID
        textposition='top center',
        hovertext=transition_hover,  # Hover shows extended transition info
        hoverinfo='text',
        name='Transitions'
    ))
    
    # Add arrows for edges (source -> transition, transition -> target)
    annotations = []
    for edge in transition_edges:
        src, mid, tgt = edge
        annotations.append(dict(
            x=mid[0],
            y=mid[1],
            ax=src[0],
            ay=src[1],
            xref='x', yref='y',
            axref='x', ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor='black',
            opacity=0.5,
            standoff=2
        ))
        annotations.append(dict(
            x=tgt[0],
            y=tgt[1],
            ax=mid[0],
            ay=mid[1],
            xref='x', yref='y',
            axref='x', ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor='black',
            opacity=0.5,
            standoff=2
        ))
    
    fig.update_layout(
        annotations=annotations,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        hovermode='closest',
        margin=dict(l=100, r=100, t=100, b=100),
        plot_bgcolor='white',   # sets the plot area background
        paper_bgcolor='white'   # sets the area around the plot
    )
    
    # Prevent hover labels from getting clipped
    fig.update_traces(cliponaxis=False)
    
    fig.show()

