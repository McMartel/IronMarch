# -*- coding: UTF-8 -*-

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

import pickle

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd

import holoviews as hv
from bokeh.models import HoverTool
hv.extension('bokeh')
renderer = hv.renderer('bokeh')

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Pandas DataFrame of edges, generated by `generat_gexf.py`
INPUT_EDGES_DF = '../output/message_edges.df'

# gexf file generated bu Gephi
INPUT_GEXF = '../output/gephi_messages.gexf'

# CSV files for post and member data
INPUT_POSTS_CSV = '../csv/forums_posts.csv'
INPUT_MEMBERS_CSV = '../csv/core_members.csv'

# file to save visualization to (without `.html` extension)
OUTPUT_HTML = '../output/message_graph'

# scaling factors for visualization glyphs
EDGE_SCALING = 0.5
NODE_SCALING = 2.

# xmin, ymin, xmax, ymax of positions of graph nodes
GRAPH_EXTENTS = (-1600, -250, 100, 1450)

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

if __name__ == '__main__':

  # 1. parse Gephi-generated GEXF file to extract node positions and size
  #############################################################################

  # parse GEXF file using `xml` parser
  #---------------------------------------------------------------------------#

  with open(INPUT_GEXF, 'r') as f:
    data = f.read()

  soup = BeautifulSoup( data, 'xml' )
  nodes = soup.find('nodes')

  # get list of all nodes
  nodes = nodes.find_all('node')

  # extract node locations and other attributes, store in DataFrame
  #---------------------------------------------------------------------------#

  # initialize empty lists to hold ordered node attributes
  node_id = []
  node_x = []
  node_y = []
  node_size = []

  # loop over all nodes
  for node in nodes:

    # extract attributes for a given node, append to relevant lists
    node_id.append(node['id'])
    node_x.append(float(node.find('viz:position')['x']))
    node_y.append(float(node.find('viz:position')['y']))
    node_size.append(float(node.find('viz:size')['value']))

  # store node attribute data in Pandas DataFrame, with appropriate type
  # conversions and scaling
  nodes_df = pd.DataFrame()
  nodes_df['x'] = node_x
  nodes_df['y'] = node_y
  nodes_df['index'] = node_id
  nodes_df['size'] = np.asarray(node_size, dtype = np.float)
  nodes_df['size'] /= NODE_SCALING
  nodes_df['member_id'] = node_id

  # 2. use DataFrames to get the number of posts, number of messages, and
  # username for each node (user)
  #############################################################################

  # read forum posts database CSV file into Pandas DataFrame
  fdf = pd.read_csv( INPUT_POSTS_CSV )

  # read pickled file of edge information generated by `generate_gexf.py` into
  # Pandas DataFrame
  edges_df = pd.read_pickle( INPUT_EDGES_DF )

  # initialize empty lists for storing the number of messages and posts a user
  # (node) made
  user_messages = [ ]
  user_posts = [ ]

  # loop over node indices
  for nid in node_id:

    # total number of messages user was either sender or recipient of
    num_msg = np.sum(edges_df[edges_df['source'] == int(nid)]['weight']) \
      + np.sum(edges_df[edges_df['target'] == int(nid)]['weight'])
    user_messages.append(num_msg)

    # total number of posts user made
    num_post = np.sum(fdf['author_id'] == int(nid))
    user_posts.append(num_post)

  # store ordered lists of user posts and user messages in DataFrame
  nodes_df['posts'] = user_posts
  nodes_df['messages'] = user_messages

  # map user index to username, store as DataFrame column
  #---------------------------------------------------------------------------#

  # read user information database CSV file into Pandas DataFrame
  udf = pd.read_csv( INPUT_MEMBERS_CSV )

  # create dict that maps user index to username
  names_dict = dict(zip(udf['member_id'].astype(str), udf['name']))

  # apply mapping dict to list of user indices, store in DataFrame
  nodes_df['name'] = [names_dict.get(nid, 'Guest') for nid in node_id ]

  # 3. prepare edge DataFrame
  #############################################################################

  # convert `source` and `target` columns to str datatype
  edges_df['source'] = edges_df['source'].astype(str)
  edges_df['target'] = edges_df['target'].astype(str)

  # use natural logarithm of edge weight, for visualization purposes
  edges_df['weight'] = np.log(edges_df['weight'].astype(float))

  # scale edge weight for visualization purposes
  edges_df['weight'] /= EDGE_SCALING

  # 4. generate visualization using HoloViews package
  #############################################################################

  # convert node DataFrame to HoloViews object
  hv_nodes = hv.Nodes(nodes_df).sort()

  # create HoloViews Graph object from nodes and edges, with x and y limits
  # bounded by `GRAPH_EXTENTS`
  hv_graph = hv.Graph(
    (edges_df, hv_nodes),
    extents = GRAPH_EXTENTS)

  # define custom hover tooltip
  hover = HoverTool(tooltips=[
    ("member id", "@member_id"),
    ("name", "@name"),
    ("posts", "@posts"),
    ("messages", "@messages"),])

  # specify parameters for visualization
  hv_graph.opts(
    node_radius='size',
    edge_color = 'white',
    node_color = '#ff9c03',
    node_hover_fill_color = '#EF4E02',
    edge_alpha = 0.2,
    edge_line_width='weight',
    edge_hover_line_color = '#DF0000',
    responsive=True,
    aspect = 1,
    bgcolor = 'black',
    tools = [hover],
    xticks = 0,
    yticks = 0,
    xlabel = '',
    ylabel = '')

  # save visualization to HTML file
  renderer.save(hv_graph, OUTPUT_HTML)

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#