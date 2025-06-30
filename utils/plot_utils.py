import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def create_dual_axis_plot(root, title, x_label, y1_label, y2_label, color1='black', color2='red'):
    fig, ax1 = plt.subplots(figsize = (6, 3))
    ax2 = ax1.twinx()

    line1, = ax1.plot([], [], label = y1_label, color = color1)
    line2, = ax2.plot([], [], label = y2_label, color = color2)

    ax1.set_title(title)
    ax1.set_xlabel(x_label)
    ax1.set_ylabel(y1_label, color = color1)
    ax2.set_ylabel(y2_label, color = color2)
    ax1.grid(True)

    canvas = FigureCanvasTkAgg(fig, master = root)
    canvas.get_tk_widget().pack(fill = 'both', expand = True)

    return fig, ax1, ax2, line1, line2, canvas


def create_single_axis_plot(root, title, x_label, y_label, color='blue'):
    fig, ax = plt.subplots()
    line, = ax.plot([], [], label = y_label, color = color)

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True)

    canvas = FigureCanvasTkAgg(fig, master = root)
    canvas.get_tk_widget().pack(fill = 'both', expand = True)

    return fig, ax, line, canvas


def update_plot(line_data_pairs, axes, canvas):
    for line, data in line_data_pairs:
        line.set_data(*data)
    for ax in axes:
        ax.relim()
        ax.autoscale_view()
    canvas.draw_idle()
